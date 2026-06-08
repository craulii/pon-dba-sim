//
// Generated file, do not edit! Created by opp_msgtool 6.0 from src/PONMessages.msg.
//

// Disable warnings about unused variables, empty switch stmts, etc:
#ifdef _MSC_VER
#  pragma warning(disable:4101)
#  pragma warning(disable:4065)
#endif

#if defined(__clang__)
#  pragma clang diagnostic ignored "-Wshadow"
#  pragma clang diagnostic ignored "-Wconversion"
#  pragma clang diagnostic ignored "-Wunused-parameter"
#  pragma clang diagnostic ignored "-Wc++98-compat"
#  pragma clang diagnostic ignored "-Wunreachable-code-break"
#  pragma clang diagnostic ignored "-Wold-style-cast"
#elif defined(__GNUC__)
#  pragma GCC diagnostic ignored "-Wshadow"
#  pragma GCC diagnostic ignored "-Wconversion"
#  pragma GCC diagnostic ignored "-Wunused-parameter"
#  pragma GCC diagnostic ignored "-Wold-style-cast"
#  pragma GCC diagnostic ignored "-Wsuggest-attribute=noreturn"
#  pragma GCC diagnostic ignored "-Wfloat-conversion"
#endif

#include <iostream>
#include <sstream>
#include <memory>
#include <type_traits>
#include "PONMessages_m.h"

namespace omnetpp {

// Template pack/unpack rules. They are declared *after* a1l type-specific pack functions for multiple reasons.
// They are in the omnetpp namespace, to allow them to be found by argument-dependent lookup via the cCommBuffer argument

// Packing/unpacking an std::vector
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::vector<T,A>& v)
{
    int n = v.size();
    doParsimPacking(buffer, n);
    for (int i = 0; i < n; i++)
        doParsimPacking(buffer, v[i]);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::vector<T,A>& v)
{
    int n;
    doParsimUnpacking(buffer, n);
    v.resize(n);
    for (int i = 0; i < n; i++)
        doParsimUnpacking(buffer, v[i]);
}

// Packing/unpacking an std::list
template<typename T, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::list<T,A>& l)
{
    doParsimPacking(buffer, (int)l.size());
    for (typename std::list<T,A>::const_iterator it = l.begin(); it != l.end(); ++it)
        doParsimPacking(buffer, (T&)*it);
}

template<typename T, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::list<T,A>& l)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        l.push_back(T());
        doParsimUnpacking(buffer, l.back());
    }
}

// Packing/unpacking an std::set
template<typename T, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::set<T,Tr,A>& s)
{
    doParsimPacking(buffer, (int)s.size());
    for (typename std::set<T,Tr,A>::const_iterator it = s.begin(); it != s.end(); ++it)
        doParsimPacking(buffer, *it);
}

template<typename T, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::set<T,Tr,A>& s)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        T x;
        doParsimUnpacking(buffer, x);
        s.insert(x);
    }
}

// Packing/unpacking an std::map
template<typename K, typename V, typename Tr, typename A>
void doParsimPacking(omnetpp::cCommBuffer *buffer, const std::map<K,V,Tr,A>& m)
{
    doParsimPacking(buffer, (int)m.size());
    for (typename std::map<K,V,Tr,A>::const_iterator it = m.begin(); it != m.end(); ++it) {
        doParsimPacking(buffer, it->first);
        doParsimPacking(buffer, it->second);
    }
}

template<typename K, typename V, typename Tr, typename A>
void doParsimUnpacking(omnetpp::cCommBuffer *buffer, std::map<K,V,Tr,A>& m)
{
    int n;
    doParsimUnpacking(buffer, n);
    for (int i = 0; i < n; i++) {
        K k; V v;
        doParsimUnpacking(buffer, k);
        doParsimUnpacking(buffer, v);
        m[k] = v;
    }
}

// Default pack/unpack function for arrays
template<typename T>
void doParsimArrayPacking(omnetpp::cCommBuffer *b, const T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimPacking(b, t[i]);
}

template<typename T>
void doParsimArrayUnpacking(omnetpp::cCommBuffer *b, T *t, int n)
{
    for (int i = 0; i < n; i++)
        doParsimUnpacking(b, t[i]);
}

// Default rule to prevent compiler from choosing base class' doParsimPacking() function
template<typename T>
void doParsimPacking(omnetpp::cCommBuffer *, const T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimPacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

template<typename T>
void doParsimUnpacking(omnetpp::cCommBuffer *, T& t)
{
    throw omnetpp::cRuntimeError("Parsim error: No doParsimUnpacking() function for type %s", omnetpp::opp_typename(typeid(t)));
}

}  // namespace omnetpp

namespace pon_dba_sim {

Register_Class(DataPacket)

DataPacket::DataPacket(const char *name, short kind) : ::omnetpp::cPacket(name, kind)
{
}

DataPacket::DataPacket(const DataPacket& other) : ::omnetpp::cPacket(other)
{
    copy(other);
}

DataPacket::~DataPacket()
{
}

DataPacket& DataPacket::operator=(const DataPacket& other)
{
    if (this == &other) return *this;
    ::omnetpp::cPacket::operator=(other);
    copy(other);
    return *this;
}

void DataPacket::copy(const DataPacket& other)
{
    this->sourceONU = other.sourceONU;
    this->trafficClass = other.trafficClass;
    this->creationTime = other.creationTime;
    this->deadline = other.deadline;
    this->dataSize = other.dataSize;
}

void DataPacket::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cPacket::parsimPack(b);
    doParsimPacking(b,this->sourceONU);
    doParsimPacking(b,this->trafficClass);
    doParsimPacking(b,this->creationTime);
    doParsimPacking(b,this->deadline);
    doParsimPacking(b,this->dataSize);
}

void DataPacket::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cPacket::parsimUnpack(b);
    doParsimUnpacking(b,this->sourceONU);
    doParsimUnpacking(b,this->trafficClass);
    doParsimUnpacking(b,this->creationTime);
    doParsimUnpacking(b,this->deadline);
    doParsimUnpacking(b,this->dataSize);
}

int DataPacket::getSourceONU() const
{
    return this->sourceONU;
}

void DataPacket::setSourceONU(int sourceONU)
{
    this->sourceONU = sourceONU;
}

int DataPacket::getTrafficClass() const
{
    return this->trafficClass;
}

void DataPacket::setTrafficClass(int trafficClass)
{
    this->trafficClass = trafficClass;
}

::omnetpp::simtime_t DataPacket::getCreationTime() const
{
    return this->creationTime;
}

void DataPacket::setCreationTime(::omnetpp::simtime_t creationTime)
{
    this->creationTime = creationTime;
}

::omnetpp::simtime_t DataPacket::getDeadline() const
{
    return this->deadline;
}

void DataPacket::setDeadline(::omnetpp::simtime_t deadline)
{
    this->deadline = deadline;
}

int DataPacket::getDataSize() const
{
    return this->dataSize;
}

void DataPacket::setDataSize(int dataSize)
{
    this->dataSize = dataSize;
}

class DataPacketDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_sourceONU,
        FIELD_trafficClass,
        FIELD_creationTime,
        FIELD_deadline,
        FIELD_dataSize,
    };
  public:
    DataPacketDescriptor();
    virtual ~DataPacketDescriptor();

    virtual bool doesSupport(omnetpp::cObject *obj) const override;
    virtual const char **getPropertyNames() const override;
    virtual const char *getProperty(const char *propertyName) const override;
    virtual int getFieldCount() const override;
    virtual const char *getFieldName(int field) const override;
    virtual int findField(const char *fieldName) const override;
    virtual unsigned int getFieldTypeFlags(int field) const override;
    virtual const char *getFieldTypeString(int field) const override;
    virtual const char **getFieldPropertyNames(int field) const override;
    virtual const char *getFieldProperty(int field, const char *propertyName) const override;
    virtual int getFieldArraySize(omnetpp::any_ptr object, int field) const override;
    virtual void setFieldArraySize(omnetpp::any_ptr object, int field, int size) const override;

    virtual const char *getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const override;
    virtual std::string getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const override;
    virtual omnetpp::cValue getFieldValue(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const override;

    virtual const char *getFieldStructName(int field) const override;
    virtual omnetpp::any_ptr getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const override;
};

Register_ClassDescriptor(DataPacketDescriptor)

DataPacketDescriptor::DataPacketDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(pon_dba_sim::DataPacket)), "omnetpp::cPacket")
{
    propertyNames = nullptr;
}

DataPacketDescriptor::~DataPacketDescriptor()
{
    delete[] propertyNames;
}

bool DataPacketDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<DataPacket *>(obj)!=nullptr;
}

const char **DataPacketDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = { "display",  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *DataPacketDescriptor::getProperty(const char *propertyName) const
{
    if (!strcmp(propertyName, "display")) return "i=msg/packet";
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int DataPacketDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 5+base->getFieldCount() : 5;
}

unsigned int DataPacketDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_sourceONU
        FD_ISEDITABLE,    // FIELD_trafficClass
        FD_ISEDITABLE,    // FIELD_creationTime
        FD_ISEDITABLE,    // FIELD_deadline
        FD_ISEDITABLE,    // FIELD_dataSize
    };
    return (field >= 0 && field < 5) ? fieldTypeFlags[field] : 0;
}

const char *DataPacketDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "sourceONU",
        "trafficClass",
        "creationTime",
        "deadline",
        "dataSize",
    };
    return (field >= 0 && field < 5) ? fieldNames[field] : nullptr;
}

int DataPacketDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "sourceONU") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "trafficClass") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "creationTime") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "deadline") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "dataSize") == 0) return baseIndex + 4;
    return base ? base->findField(fieldName) : -1;
}

const char *DataPacketDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "int",    // FIELD_sourceONU
        "int",    // FIELD_trafficClass
        "omnetpp::simtime_t",    // FIELD_creationTime
        "omnetpp::simtime_t",    // FIELD_deadline
        "int",    // FIELD_dataSize
    };
    return (field >= 0 && field < 5) ? fieldTypeStrings[field] : nullptr;
}

const char **DataPacketDescriptor::getFieldPropertyNames(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldPropertyNames(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

const char *DataPacketDescriptor::getFieldProperty(int field, const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldProperty(field, propertyName);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

int DataPacketDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        default: return 0;
    }
}

void DataPacketDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'DataPacket'", field);
    }
}

const char *DataPacketDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string DataPacketDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: return long2string(pp->getSourceONU());
        case FIELD_trafficClass: return long2string(pp->getTrafficClass());
        case FIELD_creationTime: return simtime2string(pp->getCreationTime());
        case FIELD_deadline: return simtime2string(pp->getDeadline());
        case FIELD_dataSize: return long2string(pp->getDataSize());
        default: return "";
    }
}

void DataPacketDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: pp->setSourceONU(string2long(value)); break;
        case FIELD_trafficClass: pp->setTrafficClass(string2long(value)); break;
        case FIELD_creationTime: pp->setCreationTime(string2simtime(value)); break;
        case FIELD_deadline: pp->setDeadline(string2simtime(value)); break;
        case FIELD_dataSize: pp->setDataSize(string2long(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'DataPacket'", field);
    }
}

omnetpp::cValue DataPacketDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: return pp->getSourceONU();
        case FIELD_trafficClass: return pp->getTrafficClass();
        case FIELD_creationTime: return pp->getCreationTime().dbl();
        case FIELD_deadline: return pp->getDeadline().dbl();
        case FIELD_dataSize: return pp->getDataSize();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'DataPacket' as cValue -- field index out of range?", field);
    }
}

void DataPacketDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: pp->setSourceONU(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_trafficClass: pp->setTrafficClass(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_creationTime: pp->setCreationTime(value.doubleValue()); break;
        case FIELD_deadline: pp->setDeadline(value.doubleValue()); break;
        case FIELD_dataSize: pp->setDataSize(omnetpp::checked_int_cast<int>(value.intValue())); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'DataPacket'", field);
    }
}

const char *DataPacketDescriptor::getFieldStructName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructName(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    };
}

omnetpp::any_ptr DataPacketDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void DataPacketDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    DataPacket *pp = omnetpp::fromAnyPtr<DataPacket>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'DataPacket'", field);
    }
}

Register_Class(ReportMessage)

ReportMessage::ReportMessage(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

ReportMessage::ReportMessage(const ReportMessage& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

ReportMessage::~ReportMessage()
{
}

ReportMessage& ReportMessage::operator=(const ReportMessage& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void ReportMessage::copy(const ReportMessage& other)
{
    this->sourceONU = other.sourceONU;
    this->queueSize_eMBB = other.queueSize_eMBB;
    this->queueSize_URLLC = other.queueSize_URLLC;
    this->queueSize_mMTC = other.queueSize_mMTC;
}

void ReportMessage::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    doParsimPacking(b,this->sourceONU);
    doParsimPacking(b,this->queueSize_eMBB);
    doParsimPacking(b,this->queueSize_URLLC);
    doParsimPacking(b,this->queueSize_mMTC);
}

void ReportMessage::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->sourceONU);
    doParsimUnpacking(b,this->queueSize_eMBB);
    doParsimUnpacking(b,this->queueSize_URLLC);
    doParsimUnpacking(b,this->queueSize_mMTC);
}

int ReportMessage::getSourceONU() const
{
    return this->sourceONU;
}

void ReportMessage::setSourceONU(int sourceONU)
{
    this->sourceONU = sourceONU;
}

int ReportMessage::getQueueSize_eMBB() const
{
    return this->queueSize_eMBB;
}

void ReportMessage::setQueueSize_eMBB(int queueSize_eMBB)
{
    this->queueSize_eMBB = queueSize_eMBB;
}

int ReportMessage::getQueueSize_URLLC() const
{
    return this->queueSize_URLLC;
}

void ReportMessage::setQueueSize_URLLC(int queueSize_URLLC)
{
    this->queueSize_URLLC = queueSize_URLLC;
}

int ReportMessage::getQueueSize_mMTC() const
{
    return this->queueSize_mMTC;
}

void ReportMessage::setQueueSize_mMTC(int queueSize_mMTC)
{
    this->queueSize_mMTC = queueSize_mMTC;
}

class ReportMessageDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_sourceONU,
        FIELD_queueSize_eMBB,
        FIELD_queueSize_URLLC,
        FIELD_queueSize_mMTC,
    };
  public:
    ReportMessageDescriptor();
    virtual ~ReportMessageDescriptor();

    virtual bool doesSupport(omnetpp::cObject *obj) const override;
    virtual const char **getPropertyNames() const override;
    virtual const char *getProperty(const char *propertyName) const override;
    virtual int getFieldCount() const override;
    virtual const char *getFieldName(int field) const override;
    virtual int findField(const char *fieldName) const override;
    virtual unsigned int getFieldTypeFlags(int field) const override;
    virtual const char *getFieldTypeString(int field) const override;
    virtual const char **getFieldPropertyNames(int field) const override;
    virtual const char *getFieldProperty(int field, const char *propertyName) const override;
    virtual int getFieldArraySize(omnetpp::any_ptr object, int field) const override;
    virtual void setFieldArraySize(omnetpp::any_ptr object, int field, int size) const override;

    virtual const char *getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const override;
    virtual std::string getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const override;
    virtual omnetpp::cValue getFieldValue(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const override;

    virtual const char *getFieldStructName(int field) const override;
    virtual omnetpp::any_ptr getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const override;
};

Register_ClassDescriptor(ReportMessageDescriptor)

ReportMessageDescriptor::ReportMessageDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(pon_dba_sim::ReportMessage)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

ReportMessageDescriptor::~ReportMessageDescriptor()
{
    delete[] propertyNames;
}

bool ReportMessageDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<ReportMessage *>(obj)!=nullptr;
}

const char **ReportMessageDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = { "display",  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *ReportMessageDescriptor::getProperty(const char *propertyName) const
{
    if (!strcmp(propertyName, "display")) return "i=msg/report";
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int ReportMessageDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 4+base->getFieldCount() : 4;
}

unsigned int ReportMessageDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_sourceONU
        FD_ISEDITABLE,    // FIELD_queueSize_eMBB
        FD_ISEDITABLE,    // FIELD_queueSize_URLLC
        FD_ISEDITABLE,    // FIELD_queueSize_mMTC
    };
    return (field >= 0 && field < 4) ? fieldTypeFlags[field] : 0;
}

const char *ReportMessageDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "sourceONU",
        "queueSize_eMBB",
        "queueSize_URLLC",
        "queueSize_mMTC",
    };
    return (field >= 0 && field < 4) ? fieldNames[field] : nullptr;
}

int ReportMessageDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "sourceONU") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "queueSize_eMBB") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "queueSize_URLLC") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "queueSize_mMTC") == 0) return baseIndex + 3;
    return base ? base->findField(fieldName) : -1;
}

const char *ReportMessageDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "int",    // FIELD_sourceONU
        "int",    // FIELD_queueSize_eMBB
        "int",    // FIELD_queueSize_URLLC
        "int",    // FIELD_queueSize_mMTC
    };
    return (field >= 0 && field < 4) ? fieldTypeStrings[field] : nullptr;
}

const char **ReportMessageDescriptor::getFieldPropertyNames(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldPropertyNames(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

const char *ReportMessageDescriptor::getFieldProperty(int field, const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldProperty(field, propertyName);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

int ReportMessageDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        default: return 0;
    }
}

void ReportMessageDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'ReportMessage'", field);
    }
}

const char *ReportMessageDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string ReportMessageDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: return long2string(pp->getSourceONU());
        case FIELD_queueSize_eMBB: return long2string(pp->getQueueSize_eMBB());
        case FIELD_queueSize_URLLC: return long2string(pp->getQueueSize_URLLC());
        case FIELD_queueSize_mMTC: return long2string(pp->getQueueSize_mMTC());
        default: return "";
    }
}

void ReportMessageDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: pp->setSourceONU(string2long(value)); break;
        case FIELD_queueSize_eMBB: pp->setQueueSize_eMBB(string2long(value)); break;
        case FIELD_queueSize_URLLC: pp->setQueueSize_URLLC(string2long(value)); break;
        case FIELD_queueSize_mMTC: pp->setQueueSize_mMTC(string2long(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ReportMessage'", field);
    }
}

omnetpp::cValue ReportMessageDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: return pp->getSourceONU();
        case FIELD_queueSize_eMBB: return pp->getQueueSize_eMBB();
        case FIELD_queueSize_URLLC: return pp->getQueueSize_URLLC();
        case FIELD_queueSize_mMTC: return pp->getQueueSize_mMTC();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'ReportMessage' as cValue -- field index out of range?", field);
    }
}

void ReportMessageDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        case FIELD_sourceONU: pp->setSourceONU(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_queueSize_eMBB: pp->setQueueSize_eMBB(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_queueSize_URLLC: pp->setQueueSize_URLLC(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_queueSize_mMTC: pp->setQueueSize_mMTC(omnetpp::checked_int_cast<int>(value.intValue())); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ReportMessage'", field);
    }
}

const char *ReportMessageDescriptor::getFieldStructName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructName(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    };
}

omnetpp::any_ptr ReportMessageDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void ReportMessageDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    ReportMessage *pp = omnetpp::fromAnyPtr<ReportMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'ReportMessage'", field);
    }
}

Register_Class(GrantMessage)

GrantMessage::GrantMessage(const char *name, short kind) : ::omnetpp::cMessage(name, kind)
{
}

GrantMessage::GrantMessage(const GrantMessage& other) : ::omnetpp::cMessage(other)
{
    copy(other);
}

GrantMessage::~GrantMessage()
{
}

GrantMessage& GrantMessage::operator=(const GrantMessage& other)
{
    if (this == &other) return *this;
    ::omnetpp::cMessage::operator=(other);
    copy(other);
    return *this;
}

void GrantMessage::copy(const GrantMessage& other)
{
    this->destONU = other.destONU;
    this->startTime = other.startTime;
    this->grantSize_eMBB = other.grantSize_eMBB;
    this->grantSize_URLLC = other.grantSize_URLLC;
    this->grantSize_mMTC = other.grantSize_mMTC;
}

void GrantMessage::parsimPack(omnetpp::cCommBuffer *b) const
{
    ::omnetpp::cMessage::parsimPack(b);
    doParsimPacking(b,this->destONU);
    doParsimPacking(b,this->startTime);
    doParsimPacking(b,this->grantSize_eMBB);
    doParsimPacking(b,this->grantSize_URLLC);
    doParsimPacking(b,this->grantSize_mMTC);
}

void GrantMessage::parsimUnpack(omnetpp::cCommBuffer *b)
{
    ::omnetpp::cMessage::parsimUnpack(b);
    doParsimUnpacking(b,this->destONU);
    doParsimUnpacking(b,this->startTime);
    doParsimUnpacking(b,this->grantSize_eMBB);
    doParsimUnpacking(b,this->grantSize_URLLC);
    doParsimUnpacking(b,this->grantSize_mMTC);
}

int GrantMessage::getDestONU() const
{
    return this->destONU;
}

void GrantMessage::setDestONU(int destONU)
{
    this->destONU = destONU;
}

::omnetpp::simtime_t GrantMessage::getStartTime() const
{
    return this->startTime;
}

void GrantMessage::setStartTime(::omnetpp::simtime_t startTime)
{
    this->startTime = startTime;
}

int GrantMessage::getGrantSize_eMBB() const
{
    return this->grantSize_eMBB;
}

void GrantMessage::setGrantSize_eMBB(int grantSize_eMBB)
{
    this->grantSize_eMBB = grantSize_eMBB;
}

int GrantMessage::getGrantSize_URLLC() const
{
    return this->grantSize_URLLC;
}

void GrantMessage::setGrantSize_URLLC(int grantSize_URLLC)
{
    this->grantSize_URLLC = grantSize_URLLC;
}

int GrantMessage::getGrantSize_mMTC() const
{
    return this->grantSize_mMTC;
}

void GrantMessage::setGrantSize_mMTC(int grantSize_mMTC)
{
    this->grantSize_mMTC = grantSize_mMTC;
}

class GrantMessageDescriptor : public omnetpp::cClassDescriptor
{
  private:
    mutable const char **propertyNames;
    enum FieldConstants {
        FIELD_destONU,
        FIELD_startTime,
        FIELD_grantSize_eMBB,
        FIELD_grantSize_URLLC,
        FIELD_grantSize_mMTC,
    };
  public:
    GrantMessageDescriptor();
    virtual ~GrantMessageDescriptor();

    virtual bool doesSupport(omnetpp::cObject *obj) const override;
    virtual const char **getPropertyNames() const override;
    virtual const char *getProperty(const char *propertyName) const override;
    virtual int getFieldCount() const override;
    virtual const char *getFieldName(int field) const override;
    virtual int findField(const char *fieldName) const override;
    virtual unsigned int getFieldTypeFlags(int field) const override;
    virtual const char *getFieldTypeString(int field) const override;
    virtual const char **getFieldPropertyNames(int field) const override;
    virtual const char *getFieldProperty(int field, const char *propertyName) const override;
    virtual int getFieldArraySize(omnetpp::any_ptr object, int field) const override;
    virtual void setFieldArraySize(omnetpp::any_ptr object, int field, int size) const override;

    virtual const char *getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const override;
    virtual std::string getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const override;
    virtual omnetpp::cValue getFieldValue(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const override;

    virtual const char *getFieldStructName(int field) const override;
    virtual omnetpp::any_ptr getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const override;
    virtual void setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const override;
};

Register_ClassDescriptor(GrantMessageDescriptor)

GrantMessageDescriptor::GrantMessageDescriptor() : omnetpp::cClassDescriptor(omnetpp::opp_typename(typeid(pon_dba_sim::GrantMessage)), "omnetpp::cMessage")
{
    propertyNames = nullptr;
}

GrantMessageDescriptor::~GrantMessageDescriptor()
{
    delete[] propertyNames;
}

bool GrantMessageDescriptor::doesSupport(omnetpp::cObject *obj) const
{
    return dynamic_cast<GrantMessage *>(obj)!=nullptr;
}

const char **GrantMessageDescriptor::getPropertyNames() const
{
    if (!propertyNames) {
        static const char *names[] = { "display",  nullptr };
        omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
        const char **baseNames = base ? base->getPropertyNames() : nullptr;
        propertyNames = mergeLists(baseNames, names);
    }
    return propertyNames;
}

const char *GrantMessageDescriptor::getProperty(const char *propertyName) const
{
    if (!strcmp(propertyName, "display")) return "i=msg/token";
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? base->getProperty(propertyName) : nullptr;
}

int GrantMessageDescriptor::getFieldCount() const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    return base ? 5+base->getFieldCount() : 5;
}

unsigned int GrantMessageDescriptor::getFieldTypeFlags(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeFlags(field);
        field -= base->getFieldCount();
    }
    static unsigned int fieldTypeFlags[] = {
        FD_ISEDITABLE,    // FIELD_destONU
        FD_ISEDITABLE,    // FIELD_startTime
        FD_ISEDITABLE,    // FIELD_grantSize_eMBB
        FD_ISEDITABLE,    // FIELD_grantSize_URLLC
        FD_ISEDITABLE,    // FIELD_grantSize_mMTC
    };
    return (field >= 0 && field < 5) ? fieldTypeFlags[field] : 0;
}

const char *GrantMessageDescriptor::getFieldName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldName(field);
        field -= base->getFieldCount();
    }
    static const char *fieldNames[] = {
        "destONU",
        "startTime",
        "grantSize_eMBB",
        "grantSize_URLLC",
        "grantSize_mMTC",
    };
    return (field >= 0 && field < 5) ? fieldNames[field] : nullptr;
}

int GrantMessageDescriptor::findField(const char *fieldName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    int baseIndex = base ? base->getFieldCount() : 0;
    if (strcmp(fieldName, "destONU") == 0) return baseIndex + 0;
    if (strcmp(fieldName, "startTime") == 0) return baseIndex + 1;
    if (strcmp(fieldName, "grantSize_eMBB") == 0) return baseIndex + 2;
    if (strcmp(fieldName, "grantSize_URLLC") == 0) return baseIndex + 3;
    if (strcmp(fieldName, "grantSize_mMTC") == 0) return baseIndex + 4;
    return base ? base->findField(fieldName) : -1;
}

const char *GrantMessageDescriptor::getFieldTypeString(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldTypeString(field);
        field -= base->getFieldCount();
    }
    static const char *fieldTypeStrings[] = {
        "int",    // FIELD_destONU
        "omnetpp::simtime_t",    // FIELD_startTime
        "int",    // FIELD_grantSize_eMBB
        "int",    // FIELD_grantSize_URLLC
        "int",    // FIELD_grantSize_mMTC
    };
    return (field >= 0 && field < 5) ? fieldTypeStrings[field] : nullptr;
}

const char **GrantMessageDescriptor::getFieldPropertyNames(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldPropertyNames(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

const char *GrantMessageDescriptor::getFieldProperty(int field, const char *propertyName) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldProperty(field, propertyName);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    }
}

int GrantMessageDescriptor::getFieldArraySize(omnetpp::any_ptr object, int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldArraySize(object, field);
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        default: return 0;
    }
}

void GrantMessageDescriptor::setFieldArraySize(omnetpp::any_ptr object, int field, int size) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldArraySize(object, field, size);
            return;
        }
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set array size of field %d of class 'GrantMessage'", field);
    }
}

const char *GrantMessageDescriptor::getFieldDynamicTypeString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldDynamicTypeString(object,field,i);
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        default: return nullptr;
    }
}

std::string GrantMessageDescriptor::getFieldValueAsString(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValueAsString(object,field,i);
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        case FIELD_destONU: return long2string(pp->getDestONU());
        case FIELD_startTime: return simtime2string(pp->getStartTime());
        case FIELD_grantSize_eMBB: return long2string(pp->getGrantSize_eMBB());
        case FIELD_grantSize_URLLC: return long2string(pp->getGrantSize_URLLC());
        case FIELD_grantSize_mMTC: return long2string(pp->getGrantSize_mMTC());
        default: return "";
    }
}

void GrantMessageDescriptor::setFieldValueAsString(omnetpp::any_ptr object, int field, int i, const char *value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValueAsString(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        case FIELD_destONU: pp->setDestONU(string2long(value)); break;
        case FIELD_startTime: pp->setStartTime(string2simtime(value)); break;
        case FIELD_grantSize_eMBB: pp->setGrantSize_eMBB(string2long(value)); break;
        case FIELD_grantSize_URLLC: pp->setGrantSize_URLLC(string2long(value)); break;
        case FIELD_grantSize_mMTC: pp->setGrantSize_mMTC(string2long(value)); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'GrantMessage'", field);
    }
}

omnetpp::cValue GrantMessageDescriptor::getFieldValue(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldValue(object,field,i);
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        case FIELD_destONU: return pp->getDestONU();
        case FIELD_startTime: return pp->getStartTime().dbl();
        case FIELD_grantSize_eMBB: return pp->getGrantSize_eMBB();
        case FIELD_grantSize_URLLC: return pp->getGrantSize_URLLC();
        case FIELD_grantSize_mMTC: return pp->getGrantSize_mMTC();
        default: throw omnetpp::cRuntimeError("Cannot return field %d of class 'GrantMessage' as cValue -- field index out of range?", field);
    }
}

void GrantMessageDescriptor::setFieldValue(omnetpp::any_ptr object, int field, int i, const omnetpp::cValue& value) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldValue(object, field, i, value);
            return;
        }
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        case FIELD_destONU: pp->setDestONU(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_startTime: pp->setStartTime(value.doubleValue()); break;
        case FIELD_grantSize_eMBB: pp->setGrantSize_eMBB(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_grantSize_URLLC: pp->setGrantSize_URLLC(omnetpp::checked_int_cast<int>(value.intValue())); break;
        case FIELD_grantSize_mMTC: pp->setGrantSize_mMTC(omnetpp::checked_int_cast<int>(value.intValue())); break;
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'GrantMessage'", field);
    }
}

const char *GrantMessageDescriptor::getFieldStructName(int field) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructName(field);
        field -= base->getFieldCount();
    }
    switch (field) {
        default: return nullptr;
    };
}

omnetpp::any_ptr GrantMessageDescriptor::getFieldStructValuePointer(omnetpp::any_ptr object, int field, int i) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount())
            return base->getFieldStructValuePointer(object, field, i);
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        default: return omnetpp::any_ptr(nullptr);
    }
}

void GrantMessageDescriptor::setFieldStructValuePointer(omnetpp::any_ptr object, int field, int i, omnetpp::any_ptr ptr) const
{
    omnetpp::cClassDescriptor *base = getBaseClassDescriptor();
    if (base) {
        if (field < base->getFieldCount()){
            base->setFieldStructValuePointer(object, field, i, ptr);
            return;
        }
        field -= base->getFieldCount();
    }
    GrantMessage *pp = omnetpp::fromAnyPtr<GrantMessage>(object); (void)pp;
    switch (field) {
        default: throw omnetpp::cRuntimeError("Cannot set field %d of class 'GrantMessage'", field);
    }
}

}  // namespace pon_dba_sim

namespace omnetpp {

}  // namespace omnetpp

