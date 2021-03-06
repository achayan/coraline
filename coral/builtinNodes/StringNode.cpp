
#include "StringNode.h"

using namespace coral;

AddStringNode::AddStringNode(const std::string &name, Node *parent):
Node(name, parent),
_selectedOperation(0)
{
	setSliceable(true);
	_in0 = new StringAttribute("in0", this);
	_in1 = new StringAttribute("in1", this);
	_out = new StringAttribute("out", this);

	addInputAttribute(_in0);
	addInputAttribute(_in1);
	addOutputAttribute(_out);

	setAttributeAffect(_in0, _out);
	setAttributeAffect(_in1, _out);

	std::vector<std::string> specs;
	specs.push_back("String");
	specs.push_back("StringArray");
	specs.push_back("Path");
	specs.push_back("PathArray");

	setAttributeAllowedSpecializations(_in0, specs);
	setAttributeAllowedSpecializations(_in1, specs);
	setAttributeAllowedSpecializations(_out, specs);

	addAttributeSpecializationLink(_in0, _out);
	addAttributeSpecializationLink(_in1, _out);
}


void AddStringNode::updateSpecializationLink(Attribute *attrA, Attribute *attrB, std::vector<std::string> &specA, std::vector<std::string> &specB)
{
	Node::updateSpecializationLink(attrA, attrB, specA, specB);
}


void AddStringNode::attributeSpecializationChanged(Attribute *attr)
{
	_selectedOperation = 0;
	String::Type in0type = _in0->outValue()->type();
	if(in0type != String::stringTypeAny)
	{
		if (in0type == String::stringType)
		{
			_selectedOperation = &AddStringNode::updateString;
		} else if (in0type == String::pathType)
		{
			_selectedOperation = &AddStringNode::updatePath;
		}
	}
}

void AddStringNode::updateSlice(Attribute *attr, unsigned int slice)
{
	if (_selectedOperation)
	{
		(this->*_selectedOperation)(_in0->value(), _in1->value(), _out->outValue(), slice);
	}
}

void AddStringNode::updateString(String *in0, String *in1, String *out, unsigned int slice)
{
	const std::vector<std::string> in0vals = in0->stringValuesSlice(slice);
	const std::vector<std::string> in1vals = in1->stringValuesSlice(slice);
	unsigned int size = in0vals.size();
	std::vector<std::string> outVals(size);
	for (int i=0; i < size; ++i)
	{
		std::string strValue = in0vals[i];
		strValue += in1vals[i];
		outVals[i] = strValue;
	}
	out->setStringValuesSlice(slice, outVals);
}

void AddStringNode::updatePath(String *in0, String *in1, String *out, unsigned int slice)
{
	const std::vector<std::string> in0vals = in0->pathValuesSlice(slice);
	const std::vector<std::string> in1vals = in1->pathValuesSlice(slice);
	unsigned int size = in0vals.size();
	std::vector<std::string> outVals(size);
#ifdef _WIN32
	std::string osSep = "\\";
#else
	std::string osSep = "/";
#endif
	for (int i=0; i<size; ++i)
	{
		std::string strValue = in0vals[i];
		strValue += osSep + in1vals[i];
		outVals[i] = strValue;
	}
	out->setPathValuesSlice(slice, outVals);
}


BuildArrayStringNode::BuildArrayStringNode(const std::string &name, Node *parent):
Node(name, parent),
_selectedOperation(0)
{
	setSliceable(true);
	setAllowDynamicAttributes(true);
	_array = new StringAttribute("array", this);
	addOutputAttribute(_array);
}

void BuildArrayStringNode::addStringAttribute()
{
	std::string numStr = stringUtils::intToString(inputAttributes().size());
	StringAttribute *attr = new StringAttribute("in" + numStr, this);
	addInputAttribute(attr);
	setAttributeAffect(attr, _array);

	std::vector<std::string> specs;
	specs.push_back("String");
	specs.push_back("Path");
	setAttributeAllowedSpecializations(attr, specs);
	addAttributeSpecializationLink(attr, _array);

	addDynamicAttribute(attr);
	updateAttributeSpecialization(attr);
}

void BuildArrayStringNode::updateSpecializationLink(Attribute *attrA, Attribute *attrB, std::vector<std::string> &specA, std::vector<std::string> &specB)
{
	if (specA.size() <= specB.size())
	{
		specB.resize(specA.size());
		for (int i=0; i < specA.size(); ++i)
		{
			specB[i] = specA[i] + "Array";
		}
	}
	else
	{
		specA.resize(specB.size());
		for (int i=0; specB.size(); ++i)
		{
			specA[i] = stringUtils::strip(specB[i], "Array");
		}
	}
}

void BuildArrayStringNode::attributeSpecializationChanged(Attribute *attr)
{
	if (attr == _array)
	{
		_selectedOperation = 0;
		String::Type type = _array->outValue()->type();
		if (type != String::stringTypeAny)
		{
			if (type == String::stringTypeArray)
			{
				_selectedOperation = &BuildArrayStringNode::updateString;
			}
			else if (type == String::pathTypeArray)
			{
				_selectedOperation = &BuildArrayStringNode::updatePath;
			}
		}
	}
}

void BuildArrayStringNode::updateString(const std::vector<Attribute*> &inAttrs, int arraySize, String *array, unsigned int slice){
	std::vector<std::string> arrayValues(arraySize);
	for (int i=0; i < arraySize; ++i){
		String *inStr = (String*)inAttrs[i]->value();
		arrayValues[i] = inStr->stringValueAtSlice(slice, 0);
	}
	array->setStringValuesSlice(slice, arrayValues);
}

void BuildArrayStringNode::updatePath(const std::vector<Attribute*> &inAttrs, int arraySize, String *array, unsigned int slice){
	std::vector<std::string> arrayValues(arraySize);
	for (int i=0; i < arraySize; ++i){
		String *inStr = (String*)inAttrs[i]->value();
		arrayValues[i] = inStr->pathValueAtSlice(slice, 0);
	}
	array->setPathValuesSlice(slice, arrayValues);
}

void BuildArrayStringNode::updateSlice(Attribute *attr, unsigned int slice){
	if (_selectedOperation){
		std::vector<Attribute*> inAttrs = inputAttributes();
		int arraySize = inAttrs.size();
		String *array = _array->outValue();
		(this->*_selectedOperation)(inAttrs, arraySize, array, slice);
	}
}


StringArrayIndices::StringArrayIndices(const std::string &name, Node* parent): Node(name, parent)
{
	setSliceable(true);

	_array = new StringAttribute("array", this);
	_indices = new NumericAttribute("indices", this);

	addInputAttribute(_array);
	addOutputAttribute(_indices);

	setAttributeAffect(_array, _indices);

	std::vector<std::string> arraySpec;
	arraySpec.push_back("PathArray");
	arraySpec.push_back("StringArray");

	setAttributeAllowedSpecializations(_array, arraySpec);
	setAttributeAllowedSpecialization(_indices, "IntArray");
}

void StringArrayIndices::updateSlice(Attribute *attribute, unsigned int slice)
{
	int arraySize = _array->value()->sizeSlice(slice);
	std::vector<int> indices(arraySize);

	for (int i=0; i < arraySize; ++i)
	{
		indices[i] = i;
	}

	_indices->outValue()->setIntValuesSlice(slice, indices);
}

GetStringArrayElement::GetStringArrayElement(const std::string &name, Node *parent):
	Node(name, parent),
	_selectedOperation(0)
{
	setSliceable(true);

	_array = new StringAttribute("array", this);
	_index = new NumericAttribute("index", this);
	_element = new StringAttribute("element", this);

	addInputAttribute(_array);
	addInputAttribute(_index);
	addOutputAttribute(_element);

	setAttributeAffect(_array, _element);
	setAttributeAffect(_index, _element);

	std::vector<std::string> arraySpec;
	arraySpec.push_back("StringArray");
	arraySpec.push_back("PathArray");

	std::vector<std::string> elemSpec;
	elemSpec.push_back("String");
	elemSpec.push_back("Path");
	elemSpec.push_back("StringArray");
	elemSpec.push_back("PathArray");

	std::vector<std::string> indexSpec;
	indexSpec.push_back("Int");
	indexSpec.push_back("IntArray");

	setAttributeAllowedSpecializations(_array, arraySpec);
	setAttributeAllowedSpecializations(_index, indexSpec);
	setAttributeAllowedSpecializations(_element, elemSpec);
}

void GetStringArrayElement::updateSpecializationLink(Attribute *attrA, Attribute *attrB, std::vector<std::string> &specA, std::vector<std::string> &specB)
{
	if (attrA == _array)
	{
		std::vector<std::string> newSpecA;
		for (int i=0; i < specA.size(); ++i){
			std::string &sA = specA[i];
			std::string typeA = stringUtils::strip(sA, "Array");
			for (int j=0; j < specB.size(); ++j){
				std::string typeB = stringUtils::strip(specB[j], "Array");
				if (typeA == typeB){
					newSpecA.push_back(sA);
					break;
				}
			}
		}

		std::vector<std::string> newSpecB;
		for (int i=0; i<specB.size(); ++i){
			std::string &sB = specB[i];
			std::string typeB = stringUtils::strip(sB, "Array");
			for (int j=0; j < specA.size(); ++j){
				newSpecB.push_back(sB);
				break;
			}
		}

		specA = newSpecA;
		specB = newSpecB;
	}
	else {
		if (specA.size() == 1){
			std::string specAsuffix = "";
			if (stringUtils::endswith(specA[0], "Array")){
				specAsuffix = "Array";
			}

			std::vector<std::string> newSpecB;
			for (int i=0; i < specB.size(); ++i){
				std::string &sB = specB[i];
				std::string specBsuffix = "";
				if (stringUtils::endswith(sB, "Array")){
					specBsuffix = "Array";
				}

				if (specAsuffix == specBsuffix){
					newSpecB.push_back(sB);
				}
			}

			specB = newSpecB;
		}
		else {
			std::vector<std::string> newSpecA;
			for (int i=0; i < specB.size(); ++i){
				std::string &sB = specB[i];
				if (!stringUtils::endswith(sB, "Array")){
					newSpecA.push_back("Int");
					break;
				}
			}

			for (int i=0; i < specB.size(); ++i){
				std::string &sB = specB[i];
				if (stringUtils::endswith(sB, "Array")){
					newSpecA.push_back("IntArray");
					break;
				}
			}

			specA = newSpecA;
		}
	}
}

void GetStringArrayElement::attributeSpecializationChanged(Attribute *attribute){
	if (attribute == _array){
		_selectedOperation = 0;

		String::Type type = _array->outValue()->type();
		if (type != String::stringTypeAny)
		{
			if (type == String::stringTypeArray){
				_selectedOperation = &GetStringArrayElement::updateString;
			}
			else if (type == String::pathTypeArray){
				_selectedOperation = &GetStringArrayElement::updatePath;
			}
		}
	}
}

void GetStringArrayElement::updateString(String *array, const std::vector<int> &index, String *element, unsigned int slice){
	int size = index.size();
	element->resize(size);
	for (int i=0; i < size; ++i){
		std::string v = array->stringValueAtSlice(slice, index[i]);
		element->setStringValueAtSlice(slice, i, v);
	}
}

void GetStringArrayElement::updatePath(String *array, const std::vector<int> &index, String *element, unsigned int slice){
	int size = index.size();
	element->resize(size);
	for (int i=0; i<size; ++i){
		std::string v = array->pathValueAtSlice(slice, index[i]);
		element->setPathValueAtSlice(slice, i, v);
	}
}

void GetStringArrayElement::updateSlice(Attribute *attribute, unsigned int slice){
	if (_selectedOperation){
		String *array = _array->value();
		std::vector<int> index = _index->value()->intValuesSlice(slice);
		String *element = _element->outValue();
		(this->*_selectedOperation)(array, index, element, slice);
	}
}

StringArraySize::StringArraySize(const std::string &name, Node *parent): Node(name, parent)
{
	setSliceable(true);

	_array = new StringAttribute("array", this);
	_size = new NumericAttribute("size", this);

	addInputAttribute(_array);
	addOutputAttribute(_size);

	setAttributeAffect(_array, _size);

	std::vector<std::string> arraySpec;
	arraySpec.push_back("StringArray");
	arraySpec.push_back("PathArray");

	setAttributeAllowedSpecializations(_array, arraySpec);
	setAttributeAllowedSpecialization(_size, "Int");
}

void StringArraySize::updateSlice(Attribute *attribute, unsigned int slice)
{
	String *array = _array->value();
	if (array->type() != String::stringTypeAny)
	{
		_size->outValue()->setIntValueAtSlice(slice, 0, array->size());
	}
	else
	{
		setAttributeIsClean(_size, false);
	}
}