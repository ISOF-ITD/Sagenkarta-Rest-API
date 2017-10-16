from .models import Records, Persons, Socken
from rest_framework import viewsets
from .serializers import RecordsSerializer, SingleRecordSerializer, PersonsSerializer, SockenSerializer
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

class RecordsViewSet(viewsets.ReadOnlyModelViewSet):
	serializer_class = RecordsSerializer

	def get_queryset(self):
		queryset = Records.objects.all()

		filters = {}
		
		country = self.request.query_params.get('country', None)
		if country is not None:
			filters['country__iexact'] = country

		only_categories = self.request.query_params.get('only_categories', None)
		if only_categories is not None:
			queryset = queryset.exclude(category='')

		category = self.request.query_params.get('category', None)
		if category is not None:
			category_values = category.upper().split(',')
			filters['category__in'] = category_values

		record_ids = self.request.query_params.get('record_ids', None)
		if record_ids is not None:
			record_id_list = record_ids.upper().split(',')
			filters['id__in'] = record_id_list

		type = self.request.query_params.get('type', None)
		if type is not None:
			type_values = type.split(',')
			filters['type__in'] = type_values

		person = self.request.query_params.get('person', None)
		if person is not None:
			filters['persons__id'] = person

		place = self.request.query_params.get('place', None)
		if place is not None:
			filters['places__id'] = place

		gender = self.request.query_params.get('gender', None)
		if gender is not None:
			person_relation = self.request.query_params.get('person_relation', None)
			filters['persons__gender__icontains'] = gender.lower()

		search_string = self.request.query_params.get('search', None)
		if search_string is not None:
			search_field = self.request.query_params.get('search_field', 'record')
			search_string = search_string.lower();

			if search_field.lower() == 'record':
				queryset = queryset.filter(Q(title__icontains=search_string) | Q(text__icontains=search_string))
			elif search_field.lower() == 'person':
				filters['persons__name__icontains'] = search_string
			elif search_field.lower() == 'place':
				queryset = queryset.filter(Q(places__name__icontains=search_string) | Q(places__harad__name__icontains=search_string) | Q(places__harad__lan__icontains=search_string) | Q(places__harad__landskap__icontains=search_string))

		record_ids = self.request.query_params.get('record_ids', None)
		if record_ids is not None:
			record_id_list = record_ids.split(',')
			filters['id__in'] = record_id_list

		queryset = queryset.filter(**filters).distinct()

		print(queryset.query)

		return queryset

	def retrieve(self, request, pk=None):
		queryset = Records.objects.all()
		record = get_object_or_404(queryset, pk=pk)
		serializer = SingleRecordSerializer(record)
		return Response(serializer.data)

class PersonsViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = Persons.objects.all()
	serializer_class = PersonsSerializer


class LocationsViewSet(viewsets.ReadOnlyModelViewSet):
	def get_queryset(self):
		country = self.request.query_params.get('country', None)
		category = self.request.query_params.get('category', None)
		type = self.request.query_params.get('type', None)
		only_categories = self.request.query_params.get('only_categories', None)
		search_string = self.request.query_params.get('search', None)
		search_field = self.request.query_params.get('search_field', 'record')
		record_ids = self.request.query_params.get('record_ids', None)
		person_relation = self.request.query_params.get('person_relation', None)
		gender = self.request.query_params.get('gender', None)
		
		joins = []
		where = []
		
		if country is not None or category is not None or type is not None or only_categories is not None or search_string is not None or record_ids is not None:
			joins.append('LEFT JOIN records_places ON records_places.place = socken.id')
			joins.append('LEFT JOIN records ON records.id = records_places.record')

		if (search_string is not None and search_field == 'person') or gender is not None:
			joins.append('LEFT JOIN records_persons ON records_persons.record = records.id')
			joins.append('LEFT JOIN persons ON records_persons.person = persons.id')

		if search_string is not None:
			if search_field.lower() == 'record':
				if search_string.find(';') > -1:
					where.append('MATCH(records.text) AGAINST("'+search_string.replace(';', '+')+'")')
				else:
					where.append('(LOWER(records.title) LIKE "%%'+search_string.lower()+'%%" OR LOWER(records.text) LIKE "%%'+search_string.lower()+'%%" OR LOWER(records.archive_id) LIKE "%%'+search_string.lower()+'%%")')
			elif search_field.lower() == 'person':
				where.append('(LOWER(persons.name) LIKE "%%'+search_string.lower()+'%%")')
			elif search_field.lower() == 'place':
				where.append((
					'('
					'LOWER(harad.name) LIKE "%%'+search_string.lower()+'%%" OR '
					'LOWER(harad.landskap) LIKE "%%'+search_string.lower()+'%%" OR '
					'LOWER(harad.lan) LIKE "%%'+search_string.lower()+'%%" OR '
					'LOWER(socken.fylke) LIKE "%%'+search_string.lower()+'%%" OR '
					'LOWER(socken.name) LIKE "%%'+search_string.lower()+'%%"'
					')'
				))
				joins.append('LEFT JOIN harad ON harad.id = socken.harad')

		if record_ids is not None:
			if record_ids.find(',') > -1:
				record_id_list = record_ids.split(',')
				record_id_criteria = '(records.id = '+' OR records.id = '.join(record_id_list)+')'
				where.append(record_id_criteria)
			else:
				where.append('LOWER(records.id) = "'+record_ids+'"')

		if type is not None:
			if type.find(',') > -1:
				types = type.split(',')
				type_criteria = '(LOWER(records.type) = "'+'" OR LOWER(records.type) = "'.join(types)+'")'
				where.append(type_criteria)
			else:
				where.append('LOWER(records.type) = "'+type.lower()+'"')

		if category is not None:
			if category.find(',') > -1:
				categories = category.split(',')
				category_criteria = '(LOWER(records.category) = "'+'" OR LOWER(records.category) = "'.join(categories)+'")';
				where.append(category_criteria)
			else:
				where.append('LOWER(records.category) = "'+category.lower()+'"')

		if person_relation is not None:
			where.append('LOWER(records_persons.relation) = "'+person_relation.lower()+'"')

		if gender is not None:
			where.append('LOWER(persons.gender) = "'+gender.lower()+'"')

		if only_categories is not None and only_categories == True:
			where.join('records.category != ""')

		if country is not None:
			if country.find(',') > -1:
				countries = country.split(',')
				country_criterias = '(LOWER(records.country) = "'+'" OR LOWER(records.country) = "'.join(countries)+'")';
				where.append(country_criterias)
			else:
				where.append('LOWER(records.country) = "'+country.lower()+'"')

		where.append('socken.lat IS NOT NULL')
		where.append('socken.lng IS NOT NULL')

		#joins.append('LEFT JOIN harad ON harad.id = socken.harad')

		sql = 'SELECT DISTINCT socken.id, socken.name, socken.lat, socken.lng, socken.lmId lm_id, socken.fylke FROM socken '+((' '.join(joins) if len(joins) > 0 else '')+' WHERE '+(' AND '.join(where) if len(where) > 0 else ''))+' GROUP BY socken.id'

		print(sql)
		queryset = Socken.objects.raw(sql)

		return queryset

	def retrieve(self, request, pk=None):
		queryset = Socken.objects.all()
		socken = get_object_or_404(queryset, pk=pk)
		serializer = SockenSerializer(socken)
		return Response(serializer.data)

	def paginate_queryset(self, queryset, view=None):
		return None

	serializer_class = SockenSerializer

class _LocationsViewSet(viewsets.ReadOnlyModelViewSet):
	def get_queryset(self):
		queryset = Socken.objects.all()

		filters = {}

		country = self.request.query_params.get('country', None)
		if country is not None:
			#queryset = queryset.filter(socken_records__country=country)
			filters['socken_records__country'] = country

		category = self.request.query_params.get('category', None)
		if category is not None:
			#queryset = queryset.filter(socken_records__category=category)
			filters['socken_records__category'] = category.upper()

		type = self.request.query_params.get('type', None)
		if type is not None:
			type_values = type.split(',')
			#queryset = queryset.filter(socken_records__type__in=type_values).distinct()
			filters['socken_records__type__in'] = type_values

		search_string = self.request.query_params.get('search', None)
		if search_string is not None:
			search_field = self.request.query_params.get('search_field', 'record')

			if search_field.lower() == 'record':
				queryset = queryset.filter(Q(socken_records__title__icontains=search_string) | Q(socken_records__text__icontains=search_string))
			if search_field.lower() == 'person':
				filters['socken_records__persons__name__icontains'] = search_string

		only_categories = self.request.query_params.get('only_categories', None)
		if only_categories is not None:
			#queryset = queryset.filter(~Q(socken_records__category=None))
			queryset = queryset.exclude(socken_records__category='')

		queryset = queryset.filter(**filters).distinct()

		print(queryset.query)

		return queryset

	def paginate_queryset(self, queryset, view=None):
		return None

	serializer_class = SockenSerializer