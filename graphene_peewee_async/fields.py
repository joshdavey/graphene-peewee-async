import asyncio
from functools import partial

from graphene import Field, List, ConnectionField, Argument, String, Int, Connection
from graphene.types.generic import GenericScalar

from .queries import get_query, TOTAL_FIELD
from .utils import maybe_query


FILTERS_FIELD = 'filters'
ORDER_BY_FIELD = 'order_by'
PAGE_FIELD = 'page'
PAGINATE_BY_FIELD = 'paginate_by'


class PeeweeConnection(Connection):

    count = Int()
    total = Int()

    def resolve_count(self, info, **args):
        return len(self.edges)

    def resolve_total(self, info, **args):
        if self.edges:
            result = getattr(self.edges[0].node, TOTAL_FIELD, None)
            if result is None:
                return len(self.edges)
            return result
        return 0

    class Meta:
        abstract = True


class PeeweeConnectionField(ConnectionField):

    def __init__(self, type, *args, **kwargs):
        kwargs.update({
            FILTERS_FIELD: Argument(GenericScalar),
            ORDER_BY_FIELD: Argument(List(String)),
            PAGE_FIELD: Argument(Int),
            PAGINATE_BY_FIELD: Argument(Int)
        })
        super(PeeweeConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def model(self):
        return self.type._meta.node._meta.model

    @asyncio.coroutine
    def query_resolver(self, resolver, root, info, **args):
        query = resolver(root, info, **args)
        if query is None:
            filters = args.get(FILTERS_FIELD, {})
            order_by = args.get(ORDER_BY_FIELD, [])
            page = args.get(PAGE_FIELD, None)
            paginate_by = args.get(PAGINATE_BY_FIELD, None)
            query = get_query(self.model, info, filters=filters, order_by=order_by, page=page, paginate_by=paginate_by)
        return (yield from self.model._meta.manager.execute(query))

    def get_resolver(self, parent_resolver):
        return super().get_resolver(partial(self.query_resolver, parent_resolver))


class PeeweeListField(Field):

    def __init__(self, _type, *args, **kwargs):
        super(PeeweeListField, self).__init__(List(_type), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @staticmethod
    def list_resolver(resolver, root, info, **args):
        return maybe_query(resolver(root, info, **args))

    def get_resolver(self, parent_resolver):
        return partial(self.list_resolver, parent_resolver)
