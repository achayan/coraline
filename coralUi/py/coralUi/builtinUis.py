# <license>
# Copyright (C) 2011 Andrea Interguglielmi, All rights reserved.
# This file is part of the coral repository downloaded from http://code.google.com/p/coral-repo.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# </license>

import  logging
import  traceback
import  weakref

from    PyQt4   import  QtCore
from    PyQt4   import  QtGui

import  viewport
from    coral                       import  coralApp
from    coral                       import  utils
from    coral.observer              import  Observer
from    nodeEditor.attributeUi      import  AttributeUi
from    nodeEditor.nodeEditor       import  NodeEditor
from    nodeEditor.nodeUi           import  NodeUi
from    nodeInspector               import  custompythonnodeinspector
from    nodeInspector.fields        import  IntValueField
from    nodeInspector.fields        import  FloatValueField
from    nodeInspector.fields        import  BoolValueField
from    nodeInspector.fields        import  StringValueField
from    nodeInspector.fields        import  ColorField
from    nodeInspector.nodeInspector import  NodeInspectorWidget
from    nodeInspector.nodeInspector import  AttributeInspectorWidget
from    pluginUi                    import  PluginUi


logger = logging.getLogger("coraline")


def _findFirstConnectedAtributeNonPassThrough(coralAttribute, processedAttributes):
    foundAttr = None
    if coralAttribute not in processedAttributes:
        processedAttributes.append(coralAttribute)
        
        if coralAttribute.isPassThrough() == False:
            return coralAttribute
        else:
            if coralAttribute.input():
                foundAttr = _findFirstConnectedAtributeNonPassThrough(coralAttribute.input(), processedAttributes)
                if foundAttr:
                    return foundAttr
                    
            for out in coralAttribute.outputs():
                foundAttr = _findFirstConnectedAtributeNonPassThrough(out, processedAttributes)
                if foundAttr:
                    return foundAttr

    return foundAttr


class GeoInstanceArrayAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
        
    def hooksColor(self, specialization):
        return QtGui.QColor(240, 230, 250)


class GeoAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
        
    def hooksColor(self, specialization):
        return QtGui.QColor(200, 200, 250)


class NumericAttributeUi(AttributeUi):
    typeColor = {
        "Any": QtGui.QColor(255, 255, 95),
        "Int": QtGui.QColor(255, 107, 109),
        "Float": QtGui.QColor(5, 247, 176),
        "Vec3": QtGui.QColor(0, 120, 255),
        "Col4": QtGui.QColor(88, 228, 255),
        "Quat": QtGui.QColor(0, 255, 0),
        "Matrix44": QtGui.QColor(179, 102, 255)
        }
    
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
    
    def hooksColor(self, specialization):
        color = NumericAttributeUi.typeColor["Any"]
        
        if len(specialization) == 2:
            prefix1 = specialization[0].replace("Array", "")
            prefix2 = specialization[1].replace("Array", "")
            
            if(prefix1 == prefix2):
                color = NumericAttributeUi.typeColor[prefix1]
                        
        elif len(specialization) == 1:
            prefix = specialization[0].replace("Array", "")
            suffix = specialization[0].replace(prefix, "")
            color = NumericAttributeUi.typeColor[prefix]
            
            if suffix == "Array":
                color = color.lighter(110)
        
        return color


class NumericAttributeInspectorWidget(AttributeInspectorWidget):
    def __init__(self, coralAttribute, parentWidget, sourceCoralAttributes = []):
        AttributeInspectorWidget.__init__(self, coralAttribute, parentWidget)
        
        self._valueField = None
        self._attributeSpecializedObserver = Observer()
        
        coralApp.addAttributeSpecializedObserver(self._attributeSpecializedObserver, coralAttribute, self._specialized)
        
        self._update()
        
    def _clear(self):
        for i in range(self.layout().count()):
            widget = self.layout().takeAt(0).widget()
            
            widget.setParent(None)
            del widget
    
    def _update(self):
        attr = self.coralAttribute()
        numericAttribute = attr
        
        if attr.isPassThrough():
            processedAttrs = []
            numericAttribute = _findFirstConnectedAtributeNonPassThrough(attr, processedAttrs)
        
        valueField = None
        if numericAttribute:
            numericValue = numericAttribute.outValue()
            specializationType = numericValue.type()
            if specializationType == numericValue.numericTypeInt:
                valueField = IntValueField(attr, self)
            elif specializationType == numericValue.numericTypeFloat:
                valueField = FloatValueField(attr, self)
            elif specializationType == numericValue.numericTypeIntArray:
                if numericAttribute.value().size() == 1:
                    valueField = IntValueField(attr, self)
            elif specializationType == numericValue.numericTypeFloatArray:
                if numericAttribute.value().size() == 1:
                    valueField = FloatValueField(attr, self)
            elif specializationType == numericValue.numericTypeCol4:
                valueField = ColorField(attr, self)
            elif specializationType == numericValue.numericTypeCol4Array:
                if numericAttribute.value().size() == 1:
                    valueField = ColorField(attr, self)
        
            self._valueField = valueField
        
        if valueField is None:
            valueField = QtGui.QLabel(attr.name().split(":")[-1], self)
        
        self.layout().addWidget(valueField)
        
    def valueField(self):
        return self._valueField
        
    def _specialized(self):
        self._clear()
        self._update()


class EnumAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)

        self.setVisible(False)


class EnumAttributeInspectorWidget(AttributeInspectorWidget):
    valueChanged    = QtCore.pyqtSignal(int)
    def __init__(self, coralAttribute, parentWidget):
        AttributeInspectorWidget.__init__(self, coralAttribute, parentWidget)
        
        self._combo = QtGui.QComboBox(self)
        self._label = QtGui.QLabel(coralAttribute.name() + " ", self)
        self._hlayout = QtGui.QHBoxLayout()
        
        self._hlayout.addWidget(self._label)
        self._hlayout.addWidget(self._combo)
        self.layout().addLayout(self._hlayout)
        
        coralEnum = coralAttribute.value()
        indices = coralEnum.indices()
        i = 0
        for entry in coralEnum.entries():
            self._combo.insertItem(indices[i], entry)
            i += 1
        self._combo.setCurrentIndex(coralEnum.currentIndex())
        self._combo.currentIndexChanged.connect(self._comboChanged)

    def _comboChanged(self, index):
        self.coralAttribute().outValue().setCurrentIndex(index)
        self.coralAttribute().valueChanged()
        self.valueChanged.emit(index)

    def combo(self):
        return self._combo

    
class BoolAttributeInspectorWidget(AttributeInspectorWidget):
    def __init__(self, coralAttribute, parentWidget):
        AttributeInspectorWidget.__init__(self, coralAttribute, parentWidget)

        if coralAttribute.value().size() == 1:
            valueField = BoolValueField(coralAttribute, self)
            self.layout().addWidget(valueField)
        else:
            label = QtGui.QLabel(coralAttribute.name(), self)
            self.layout().addWidget(label)


class StringAttributeInspectorWidget(AttributeInspectorWidget):
    def __init__(self, coralAttribute, parentWidget):
        AttributeInspectorWidget.__init__(self, coralAttribute, parentWidget)
        
        valueField = StringValueField(coralAttribute, self)
        self.layout().addWidget(valueField)


class ProcessSimulationNodeInspectorWidget(NodeInspectorWidget):
    def __init__(self, coralNode, parentWidget):
        NodeInspectorWidget.__init__(self, coralNode, parentWidget)
    
    def build(self):
        NodeInspectorWidget.build(self)
        
        addAttrButton = QtGui.QPushButton("Add Input Data", self)
        self.layout().addWidget(addAttrButton)
        self.connect(addAttrButton, QtCore.SIGNAL("clicked()"), self._addInputClicked)
    
    def _addInputClicked(self):
        node = self.coralNode()
        node.addInputData()
        
        self.nodeInspector().refresh()


class AttributeSpecializationComboBox(QtGui.QComboBox):
    def __init__(self, coralAttribute, parent):
        QtGui.QComboBox.__init__(self, parent)
        
        self._coralAttribute = weakref.ref(coralAttribute)
        self._showPopupCallback = None
        self._currentItemChangedCallback = None
        self._currentItemChangedCallbackEnabled = True
        
        self.connect(self, QtCore.SIGNAL("currentIndexChanged(QString)"), self._currentItemChanged)
    
    def coralAttribute(self):
        return self._coralAttribute()

    def setShowPopupCallback(self, callback):
        self._showPopupCallback = utils.weakRef(callback)
 
    def setCurrentItemChangedCallback(self, callback):
        self._currentItemChangedCallback = utils.weakRef(callback)
    
    def _currentItemChanged(self, itemText):
        if self._currentItemChangedCallbackEnabled:
            if self._currentItemChangedCallback:
                self._currentItemChangedCallback(self)
    
    def showPopup(self):
        self._currentItemChangedCallbackEnabled = False
        
        if self._showPopupCallback:
            self._showPopupCallback(self)
        
        QtGui.QComboBox.showPopup(self)
        
        self._currentItemChangedCallbackEnabled = True


class GeoInstanceGeneratorInspectorWidget(NodeInspectorWidget):
    def __init__(self, coralNode, parentWidget):
        NodeInspectorWidget.__init__(self, coralNode, parentWidget)

    def build(self):
        NodeInspectorWidget.build(self)

        addGeoButton = QtGui.QPushButton("add input geo", self)
        self.layout().addWidget(addGeoButton)

        self.connect(addGeoButton, QtCore.SIGNAL("clicked()"), self._addGeoButtonClicked)
    
    def _addGeoButtonClicked(self):
        node = self.coralNode()
        node.addInputGeo();

        self.nodeInspector().refresh()


class RegexNodeInspectorWidget(NodeInspectorWidget):
    def build(self):
        super(RegexNodeInspectorWidget, self).build()
        self._typeWidget = self.attributeWidget("type")
        self._typeWidget.valueChanged.connect(self._typeValueChanged)
        self._groupWidget = self.attributeWidget("group")
        if self._typeWidget.combo().currentIndex() != 0:
            self._groupWidget.hide()
        self._subWidget = self.attributeWidget("sub")
        if self._typeWidget.combo().currentIndex() != 1:
            self._subWidget.hide()

    def _typeValueChanged(self):
        combo = self._typeWidget.combo()
        if combo.currentIndex() == 0:
            if self._groupWidget.isHidden():
                self._groupWidget.show()
            if not self._subWidget.isHidden():
                self._subWidget.hide()
        elif combo.currentIndex() == 1:
            if not self._groupWidget.isHidden():
                self._groupWidget.hide()
            if self._subWidget.isHidden():
                self._subWidget.show()
        elif combo.currentIndex() == 2:
            if not self._groupWidget.isHidden():
                self._groupWidget.hide()
            if not self._subWidget.isHidden():
                self._subWidget.hide()


class BuildArrayInspectorWidget(NodeInspectorWidget):
    def __init__(self, coralNode, parentWidget):
        NodeInspectorWidget.__init__(self, coralNode, parentWidget)
    
    def build(self):
        NodeInspectorWidget.build(self)
        
        addAttrButton = QtGui.QPushButton("Add Input", self)
        self.layout().addWidget(addAttrButton)
        self.connect(addAttrButton, QtCore.SIGNAL("clicked()"), self._addInputClicked)
    
    def _addInputClicked(self):
        node = self.coralNode()
        node.addNumericAttribute()
        
        self.nodeInspector().refresh()


class BuildArrayStringInspectorWidget(NodeInspectorWidget):
    def build(self):
        super(BuildArrayStringInspectorWidget, self).build()
        addAttrButton = QtGui.QPushButton("Add Input", self)
        self.layout().addWidget(addAttrButton)
        addAttrButton.clicked.connect(self._addInputClicked)
        
    def _addInputClicked(self):
        node = self.coralNode()
        node.addStringAttribute()
        self.nodeInspector().refresh()
        

class TimeNodeInspectorWidget(NodeInspectorWidget):
    def __init__(self, coralNode, parentWidget):
        NodeInspectorWidget.__init__(self, coralNode, parentWidget)
        
        self._playButton = None
        
    def build(self):
        NodeInspectorWidget.build(self)
        
        self._playButton = QtGui.QToolButton(self)
        
        self._playButton.setText("Play")
        self._playButton.setCheckable(True)
        self._playButton.setChecked(self.coralNode().isPlaying())
        self.layout().addWidget(self._playButton)
        self.connect(self._playButton, QtCore.SIGNAL("toggled(bool)"), self._playButtonToggled)
    
    def _playButtonToggled(self, play):
        if play:
            viewport.ViewportWidget._activateTimedRefresh()
            self.coralNode().play(True)
        else:
            self.coralNode().play(False)
            viewport.ViewportWidget._activateImmediateRefresh()


class PassThroughAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
        
    def hooksColor(self, specialization):
        color = QtGui.QColor(100, 100, 100)
        
        processedAttributes = []
        connectedAttribute = _findFirstConnectedAtributeNonPassThrough(self.coralAttribute(), processedAttributes)
        if connectedAttribute:
            connectedAttributeUi = NodeEditor.findAttributeUi(connectedAttribute.id())
            if connectedAttributeUi:
                color = connectedAttributeUi.hooksColor(self.coralAttribute().specialization())
        
        return color


class StringAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
        
    def hooksColor(self, specialization):
        return QtGui.QColor(204, 255, 102)


class BoolAttributeUi(AttributeUi):
    def __init__(self, coralAttribute, parentNodeUi):
        AttributeUi.__init__(self, coralAttribute, parentNodeUi)
        
    def hooksColor(self, specialization):
        color = QtGui.QColor(255, 160, 130)
        if len(specialization) == 1:
            if specialization[0].endswith("Array"):
                color.lighter(140)
        
        return color


class ForLoopNodeUi(NodeUi):
    def __init__(self, coralNode):
        NodeUi.__init__(self, coralNode)
        
        self.setCanOpenThis(True)
        self.setAttributesProxyEnabled(True)
    
    def color(self):
        return QtGui.QColor(245, 181, 118)


class CollapsedNodeUi(NodeUi):
    def __init__(self, coralNode):
        NodeUi.__init__(self, coralNode)
        
        self.setCanOpenThis(True)
        self.setAttributesProxyEnabled(True)
        self.addRightClickMenuItem("include selected nodes", self._includeSelectedNodes)

    def toolTip(self):
        tooltip = NodeUi.toolTip(self) + "\n\n"
        tooltip += "(double click to open)"
        
        return tooltip
    
    def _includeSelectedNodes(self):
        coralApp.collapseNodes(NodeEditor.selectedNodes(), collapsedNode = self.coralNode())
    
    def color(self):
        return QtGui.QColor(0, 204, 255)
    
    def repositionAmongConnectedNodes(self):
        fixedDistance = QtCore.QPointF(self.boundingRect().width() * 2.0, 0.0)
        nNodes = 0
        pos = QtCore.QPointF(0.0, 0.0)
        for attrUi in self.attributeUis():
            if attrUi.outputHook():
                for conn in attrUi.outputHook().connections():
                    pos += conn.endHook().scenePos() - fixedDistance
                    nNodes += 1
                
            elif attrUi.inputHook():
                if attrUi.inputHook().connections():
                    pos += attrUi.inputHook().connections()[0].startHook().scenePos() + fixedDistance
                    nNodes += 1
        
        if nNodes:
            pos /= nNodes
        
        finalPos = pos - self.boundingRect().center()
        self.setPos(finalPos)
        
    def repositionContainedProxys(self):
        for attrUi in self.attributeUis():
            proxyAttr = attrUi.proxy()
            if proxyAttr.pos() == QtCore.QPointF(0.0, 0.0):
                if proxyAttr.outputHook():
                    positions = []
                    for conn in proxyAttr.outputHook().connections():
                        positions.append(conn.endHook().scenePos())
                    
                    averagePos = QtCore.QPointF(0.0, 0.0)
                    for pos in positions:
                        averagePos += pos
                    
                    nPositions = len(positions)
                    if nPositions:
                        averagePos /= nPositions
                    
                    averagePos.setX(averagePos.x() - (proxyAttr.boundingRect().width() * 2.0))
                    
                    finalPos = averagePos - (proxyAttr.outputHook().scenePos() - proxyAttr.scenePos())
                    
                    proxyAttr.setPos(proxyAttr.mapFromScene(finalPos))
                
                elif proxyAttr.inputHook():
                    connections = proxyAttr.inputHook().connections()
                    if connections:
                        hookPos = connections[0].startHook().scenePos()
                        hookPos.setX(hookPos.x() + proxyAttr.boundingRect().width() * 2.0)
                        finalPos = hookPos - (proxyAttr.inputHook().scenePos() - proxyAttr.scenePos())
                        proxyAttr.setPos(finalPos)


class ShaderNodeInspectorWidget(NodeInspectorWidget):
    def __init__(self, coralNode, parentWidget):
        NodeInspectorWidget.__init__(self, coralNode, parentWidget)

        self._log = None
        self._logTimer = None
    
    def _compileShaderButtonClicked(self):
        node = self.coralNode()

        node.recompileShader()

        self.nodeInspector().refresh()

    def build(self):
        NodeInspectorWidget.build(self)

        layout = self.layout()

        compileShaderButton = QtGui.QPushButton("compile shader", self)
        layout.addWidget(compileShaderButton)
        self.connect(compileShaderButton, QtCore.SIGNAL("clicked()"), self._compileShaderButtonClicked)

        self._log = QtGui.QTextEdit(self)
        layout.addWidget(self._log)
        layout.setAlignment(self._log, QtCore.Qt.AlignTop)
        self._log.setMaximumHeight(100)
        self._log.setReadOnly(True)
        self._log.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        
        palette = self._log.palette()
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(50, 55, 60))
        self._log.setPalette(palette)
        self._log.setTextColor(QtGui.QColor(200, 190, 200))

        if self._logTimer is not None:
            self.killTimer(self._logTimer)
        
        self._logTimer = self.startTimer(500)
    
    def timerEvent(self, event):
        self._log.setText(self.coralNode().recompileShaderLog())


class ExecutableNodeInspectorWidget(NodeInspectorWidget):
    def build(self):
        super(ExecutableNodeInspectorWidget, self).build()

        self._nodeProcess = None

        processButton = QtGui.QPushButton("process", self)
        self.layout().addWidget(processButton)
        processButton.clicked.connect(self._processButtonClicked)

        resetButton = QtGui.QPushButton("reset", self)
        self.layout().addWidget(resetButton)
        resetButton.clicked.connect(self._resetButtonClicked)

        self._log = QtGui.QTextEdit(self)
        self.layout().addWidget(self._log)
        self.layout().setAlignment(self._log, QtCore.Qt.AlignTop)
        self._log.setMaximumHeight(100)
        self._log.setReadOnly(True)
        self._log.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        
        palette = self._log.palette()
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(50, 55, 60))
        self._log.setPalette(palette)
        self._log.setTextColor(QtGui.QColor(200, 190, 200))

        node = self.coralNode()
        self._log.setText(node.log())

    def _resetButtonClicked(self):
        node = self.coralNode()

        for outAttr in node.outputAttributes():
            outAttr.valueChanged()
        
        self._log.setText(node.log())

    def _processButtonClicked(self):
        node = self.coralNode()

        self._nodeProcess = ExecutableNodeProcess(node)
        self._nodeProcess.finished.connect(self._processDone)
        self._nodeProcess.error.connect(self._processError)
        self._nodeProcess.start()

    def _processError(self, exc):
        node = self.coralNode()
        # show dialog?
        self._log.setText(node.log())

    def _processDone(self):
        node = self.coralNode()
        self._log.setText(node.log())


class ExecutableNodeUi(NodeUi):
    def __init__(self, coralNode):
        super(ExecutableNodeUi, self).__init__(coralNode)

        self._progressBarPen = QtGui.QPen(QtCore.Qt.NoPen)
        self._progressBarBrush = QtGui.QBrush(QtGui.QColor(255, 204, 102))
        self._progressText = QtGui.QGraphicsSimpleTextItem(self)
        self._processModeTimer = -1

        self._progressText.setBrush(QtGui.QColor(100, 100, 100))
        self._progressText.setText("dirty")
        self._progressText.setPos(2, 100)

        coralNode.setNodeUi(self)
    
    def executableNodeChanged(self):
        node = self.coralNode()
        progressMessage = node.progressMessage()

        if progressMessage == "clean":
            self._progressBarBrush.setColor(QtGui.QColor(0, 255, 191))
        elif progressMessage == "dirty":
            self._progressBarBrush.setColor(QtGui.QColor(255, 204, 102))
        elif progressMessage == "queued":
            self._progressBarBrush.setColor(QtGui.QColor(230, 255, 102)) 
        else:
            self._progressBarBrush.setColor(QtGui.QColor(189, 0, 47))

        self._progressText.setText(progressMessage)
        
        self.update()
    
    def startProcess(self):
        coralNode = self.coralNode()
        if coralNode.progressMessage() != "clean":
            coralNode.setQueued()
            self._processModeTimer = self.startTimer(500)
    
    def endProcess(self):
        if self._processModeTimer > -1:
            self.killTimer(self._processModeTimer)
            self._processModeTimer = -1
        
        self.executableNodeChanged()

    def timerEvent(self, event):
        self.executableNodeChanged()

    def updateLayout(self):
        super(ExecutableNodeUi, self).updateLayout()
        self.resize(self.rect().width(), self.rect().height() + 20)
        self._progressText.setPos(2, self.rect().height() - 20)
    
    def paint(self, painter, option, widget):
        super(ExecutableNodeUi, self).paint(painter, option, widget)

        progressBarRect = QtCore.QRectF(self.rect())
        progressBarRect.setY(progressBarRect.height() - 19)
        progressBarRect.setHeight(17)
        progressBarRect.setX(2)
        progressBarRect.setWidth(progressBarRect.width() - 2)

        shape = QtGui.QPainterPath()
        shape.addRoundedRect(progressBarRect, 2, 2)

        painter.setPen(self._progressBarPen)
        painter.setBrush(self._progressBarBrush)
        painter.drawPath(shape)


class CollapsedExecutableNodeUi(ExecutableNodeUi, CollapsedNodeUi):
    def __init__(self, node):
        super(CollapsedExecutableNodeUi, self).__init__(node)

        self._nodes = []
        self.setCanOpenThis(True)
        self.setAttributesProxyEnabled(True)
        self.addRightClickMenuItem("include selected nodes", self._includeSelectedNodes)

        self._progressText.setText("dirty")

    def _collectChildNodes(self):
        self._nodes = []

        node = self.coralNode()
        for node in node.nodes():
            if "ExecutableNode" in node.classNames():
                self._nodes.append(node)

    def _includeSelectedNodes(self):
        coralApp.collapsedNodes(NodeEditor.selectedNodes, collapsedNode=self.coralNode())

    def color(self):
        return QtGui.QColor(73, 153, 115)

    def nodeChanged(self):
        cleanNodes = 0
        dirtyNodes = 0
        nodesProcessing = 0

        for node in self._nodes:
            progressMsg = node.progressMessage()
            if progressMsg == "clean":
                cleanNodes += 1
            elif progressMsg == "dirty":
                dirtyNodes += 1
            else:
                nodesProcessing += 1
        
        if nodesProcessing:
            self._progressBarBrush.setColor(QtGui.QColor(189, 0, 47))
            self._progressText.setText("nodes " + str(dirtyNodes + nodesProcessing))
        elif dirtyNodes == 0:
            self._progressBarBrush.setColor(QtGui.QColor(0, 255, 191))
            self._progressText.setText("clean")
        else:
            self._progressText.setText("dirty")
            self._progressBarBrush.setColor(QtGui.QColor(255, 204, 102))
        
        self.update()

    def repositionAmongConnectedNodes(self):
        self._collectChildNodes()
        self.nodeChanged()

        fixedDistance = QtCore.QPointF(self.boundingRect().width() * 2.0, 0.0)
        nNodes = 0
        pos = QtCore.QPointF(0.0, 0.0)
        for attrUi in self.attributeUis():
            if attrUi.outputHook():
                for conn in attrUi.outputHook().connections():
                    pos += conn.endHook().scenePos() - fixedDistance
                    nNodes += 1
                
            elif attrUi.inputHook():
                if attrUi.inputHook().connections():
                    pos += attrUi.inputHook().connections()[0].startHook().scenePos() + fixedDistance
                    nNodes += 1
        
        if nNodes:
            pos /= nNodes
        
        finalPos = pos - self.boundingRect().center()
        self.setPos(finalPos)
        
    def repositionContainedProxys(self):
        for attrUi in self.attributeUis():
            proxyAttr = attrUi.proxy()
            if proxyAttr.pos() == QtCore.QPointF(0.0, 0.0):
                if proxyAttr.outputHook():
                    positions = []
                    for conn in proxyAttr.outputHook().connections():
                        positions.append(conn.endHook().scenePos())
                    
                    averagePos = QtCore.QPointF(0.0, 0.0)
                    for pos in positions:
                        averagePos += pos
                    
                    nPositions = len(positions)
                    if nPositions:
                        averagePos /= nPositions
                    
                    averagePos.setX(averagePos.x() - (proxyAttr.boundingRect().width() * 2.0))
                    
                    finalPos = averagePos - (proxyAttr.outputHook().scenePos() - proxyAttr.scenePos())
                    
                    proxyAttr.setPos(proxyAttr.mapFromScene(finalPos))
                
                elif proxyAttr.inputHook():
                    connections = proxyAttr.inputHook().connections()
                    if connections:
                        hookPos = connections[0].startHook().scenePos()
                        hookPos.setX(hookPos.x() + proxyAttr.boundingRect().width() * 2.0)
                        finalPos = hookPos - (proxyAttr.inputHook().scenePos() - proxyAttr.scenePos())
                        proxyAttr.setPos(finalPos)

    def startProcess(self):
        super(CollapsedExecutableNodeUi, self).startProcess()
        self._collectChildNodes()

    def toolTip(self):
        tt = super(CollapsedExecutableNodeUi, self).toolTip() + "\n\n"
        tt += "(double click to open)"
        return tt


class ExecutableNodeProcess(QtCore.QThread):
    """ Threaded process for running Executable nodes
    """
    error       = QtCore.pyqtSignal(Exception)
    finished    = QtCore.pyqtSignal("PyQt_PyObject")

    def __init__(self, node):
        super(ExecutableNodeProcess, self).__init__()
        self._node = weakref.ref(node)
        self._nodesToUpdate = []
        self._collectNodesToUpdate(node, self._nodesToUpdate, [])

    def _collectNodesToUpdate(self, node, nodesToUpdate, walkedNodes):
        walkedNodes.append(node)

        if "ExecutableNode" in node.classNames():
            uiNode = weakref.ref(NodeEditor.findNodeUi(node.id()))
            if uiNode not in nodesToUpdate:
                nodesToUpdate.append(uiNode)
        
        for inputAttr in node.inputAttributes():
            connectedInput = inputAttr.input()
            if connectedInput:
                parentNode = connectedInput.parent()
                if parentNode not in walkedNodes:
                    self._collectNodesToUpdate(parentNode, nodesToUpdate, walkedNodes)

        for childNode in node.nodes():
            if childNode not in walkedNodes:
                self._collectNodesToUpdate(childNode, nodesToUpdate, walkedNodes)

    def run(self):
        node = self._node()
        try:
            for nodeToUpdateRef in self._nodesToUpdate:
                nodeToUpdate = nodeToUpdateRef()
                nodeToUpdate.startProcess()

            node.process()

            for nodeToUpdateRef in self._nodesToUpdate:
                nodeToUpdate = nodeToUpdateRef()
                nodeToUpdate.endProcess()
        except Exception as e:
            exc = traceback.format_exc()
            node.setLog(exc)
            self.error.emit(e)
            # print traceback.format_exc()

def loadPluginUi():
    plugin = PluginUi("builtinUis")

    plugin.registerAttributeUi("GeoInstanceArrayAttribute", GeoInstanceArrayAttributeUi)
    plugin.registerAttributeUi("GeoAttribute", GeoAttributeUi)
    plugin.registerAttributeUi("NumericAttribute", NumericAttributeUi)
    plugin.registerAttributeUi("PassThroughAttribute", PassThroughAttributeUi)
    plugin.registerAttributeUi("GeoAttribute", GeoAttributeUi)
    plugin.registerAttributeUi("StringAttribute", StringAttributeUi)
    plugin.registerAttributeUi("BoolAttribute", BoolAttributeUi)
    plugin.registerAttributeUi("EnumAttribute", EnumAttributeUi)

    plugin.registerNodeUi("CollapsedNode", CollapsedNodeUi)
    plugin.registerNodeUi("ForLoop", ForLoopNodeUi)
    plugin.registerNodeUi("ForLoop (String)", ForLoopNodeUi)
    plugin.registerNodeUi("ExecutableNode", ExecutableNodeUi)
    plugin.registerNodeUi("CollapsedExecutableNode", CollapsedExecutableNodeUi)

    plugin.registerInspectorWidget("NumericAttribute", NumericAttributeInspectorWidget)
    plugin.registerInspectorWidget("StringAttribute", StringAttributeInspectorWidget)
    plugin.registerInspectorWidget("BoolAttribute", BoolAttributeInspectorWidget)
    plugin.registerInspectorWidget("BuildArray", BuildArrayInspectorWidget)
    plugin.registerInspectorWidget("BuildArray (String)", BuildArrayStringInspectorWidget)
    plugin.registerInspectorWidget("Regex", RegexNodeInspectorWidget)
    plugin.registerInspectorWidget("Time", TimeNodeInspectorWidget)
    plugin.registerInspectorWidget("EnumAttribute", EnumAttributeInspectorWidget)
    plugin.registerInspectorWidget("ProcessSimulation", ProcessSimulationNodeInspectorWidget)
    plugin.registerInspectorWidget("GeoInstanceGenerator", GeoInstanceGeneratorInspectorWidget)
    plugin.registerInspectorWidget("Shader", ShaderNodeInspectorWidget)
    plugin.registerInspectorWidget("CustomPython", custompythonnodeinspector.CustomPythonNodeInspectorWidget)
    plugin.registerInspectorWidget("ExecutableNode", ExecutableNodeInspectorWidget)

    return plugin
