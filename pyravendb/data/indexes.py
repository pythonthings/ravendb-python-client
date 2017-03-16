from datetime import timedelta
from enum import Enum


class IndexLockMode(Enum):
    unlock = "Unlock"
    locked_ignore = "LockedIgnore"
    locked_error = "LockedError"
    side_by_side = "SideBySide"

    def __str__(self):
        return self.value


class IndexPriority(Enum):
    low = "Low"
    normal = "Normal"
    high = "High"

    def __str__(self):
        return self.value


# The sort options to use for a particular field
class SortOptions(Enum):
    # No sort options
    none = "None"
    # Sort using term values as Strings. Sort values are str and lower values are at the front.
    str = "String"
    # Sort using term values as encoded Doubles and Longs. Sort values are float or longs and lower values are at the front.
    numeric = "Numeric"

    def __str__(self):
        return self.value


class FieldIndexing(Enum):
    # Do not index the field value.
    no = "No"
    # Index the tokens produced by running the field's value through an Analyzer
    analyzed = "Analyzed"
    # Index the field's value without using an Analyzer, so it can be searched.
    not_analyzed = "NotAnalyzed"
    # Index this field using the default internal analyzer: LowerCaseKeywordAnalyzer
    default = "Default"

    def __str__(self):
        return self.value


class FieldTermVector(Enum):
    # Do not store term vectors
    no = "No"
    # Store the term vectors of each document.
    # A term vector is a list of the document's terms and their number of occurrences in that document.
    yes = "Yes"
    # store the term vector + token position information
    with_positions = "WithPositions"
    # Store the term vector + Token offset information
    with_offsets = "WithOffsets"
    # Store the term vector + Token position and offset information
    with_positions_and_offsets = "WithPositionsAndOffsets"

    def __str__(self):
        return self.value


class FieldStorage(Enum):
    # Store the original field value in the index.
    # This is useful for short texts like a document's title which should be displayed with the results.
    # The value is stored in its original form, i.e. no analyzer is used before it is stored.
    yes = "Yes"
    # Do not store the field value in the index.
    no = "No"

    def __str__(self):
        return self.value


class IndexDefinition(object):
    def __init__(self, name, index_map, configuration=None, **kwargs):
        """
        @param name: The name of the index
        :type str
        @param index_map: The map of the index
        :type str or tuple
        @param kwargs: Can be use to initialize the other option in the index definition
        :type kwargs
        """
        self.name = name
        self.configuration = configuration if configuration is not None else {}
        self.reduce = kwargs.get("reduce", None)

        self.index_id = kwargs.get("index_id", 0)
        self.is_test_index = kwargs.get("is_test_index", False)
        self.lock_mod = kwargs.get("lock_mod", None)
        self.priority = kwargs.get("priority", None)
        self.maps = (index_map,) if isinstance(index_map, str) else tuple(set(index_map, ))

        # fields is a key value dict. the key is the name of the field and the value is IndexFieldOptions
        self.fields = kwargs.get("fields", {})

    @property
    def type(self):
        value = "Map"
        if self.name and self.name.startswith('Auto/'):
            value = "AutoMap"
            if self.reduce:
                value += "Reduce"
        elif self.reduce:
            return "MapReduce"
        return value

    @property
    def is_map_reduce(self):
        return True if self.reduce else False

    @property
    def map(self):
        if not isinstance(self.maps, str):
            return self.maps[0]
        return self.maps

    @map.setter
    def map(self, value):
        if len(self.maps) != 0:
            self.maps.pop()
        self.maps.add(value)

    def to_json(self):
        return {"Configuration": self.configuration,
                "Fields": {key: self.fields[key].to_json() for key in self.fields} if len(
                    self.fields) > 0 else self.fields,
                "IndexId": self.index_id,
                "IsTestIndex": self.is_test_index,
                "LockMode": str(self.lock_mod) if self.lock_mod else None,
                "Maps": self.maps,
                "Name": self.name,
                "Reduce": self.reduce,
                "OutputReduceToCollection": None,
                "Priority": str(self.priority) if self.priority else None,
                "Type": self.type}


class IndexFieldOptions(object):
    def __init__(self, sort_options=None, indexing=None, storage=None, suggestions=None, term_vector=None,
                 analyzer=None):
        """
        @param sort_options: Sort options to use for a particular field
        :type SortOptions
        @param indexing: Options for indexing a field
        :type FieldIndexing
        @param storage: Specifies whether and how a field should be stored
        :type FieldStorage
        @param suggestions: If to produce a suggestions in query
        :type bool
        @param term_vector: Specifies whether to include term vectors for a field
        :type FieldTermVector
        @param analyzer: To make an entity property indexed using a specific Analyzer,
        :type str
        """
        self.sort_options = sort_options
        self.indexing = indexing
        self.storage = storage
        self.suggestions = suggestions
        self.term_vector = term_vector
        self.analyzer = analyzer

    def to_json(self):
        return {"Analyzer": self.analyzer,
                "Indexing": str(self.indexing) if self.indexing else None,
                "Sort": str(self.sort_options) if self.sort_options else None,
                "Spatial": None,
                "Storage": str(self.storage) if self.storage else None,
                "Suggestions": self.suggestions,
                "TermVector": str(self.term_vector) if self.term_vector else None}


class IndexQuery(object):
    def __init__(self, query="", total_size=0, skipped_results=0, default_operator=None, **kwargs):
        """
        @param query: Actual query that will be performed (Lucene syntax).
        :type str
        @param total_size: For internal use only.
        :type int
        @param skipped_results: For internal use only.
        :type int
        @param default_operator: The operator of the query (AND or OR) the default value is OR
        :type Enum.QueryOperator
        @param fetch fetch only the terms you want from the index
        :type list
    """
        self.query = query
        self.total_size = total_size
        self.skipped_results = skipped_results
        self._page_size = 128
        self.__page_size_set = False
        self.default_operator = default_operator
        self.sort_hints = kwargs.get("sort_hints", {})
        self.sort_fields = kwargs.get("sort_fields", {})
        self.fetch = kwargs.get("fetch", [])
        self.wait_for_non_stale_results = kwargs.get("wait_for_non_stale_results", False)
        self.wait_for_non_stale_results_timeout = kwargs.get("wait_for_non_stale_results_timeout", None)
        if self.wait_for_non_stale_results and not self.wait_for_non_stale_results_timeout:
            self.wait_for_non_stale_results_timeout = timedelta(minutes=15)

    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, value):
        self._page_size = value
        self.__page_size_set = True


class QueryOperator(Enum):
    OR = "OR"
    AND = "AND"
