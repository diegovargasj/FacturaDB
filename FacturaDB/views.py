import datetime

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from FacturaDB.forms import SearchForm, SearchAllForm, CancelForm
from django.template import loader
from FacturaDB.models import Factura, Rut, Client
from Facturas.settings import MEDIA_ROOT
import os
from PyPDF2 import PdfFileReader
from multiprocessing import Process

updating = False
paid_dir = 'PAGADAS'


def search(request):
	global updating
	form = SearchForm()
	cancelForm = CancelForm()
	template = loader.get_template('search.html')
	context = {}
	context['cancelForm'] = cancelForm
	if request.method == "POST":
		form = SearchForm(request.POST)
		if form.is_valid():
			if 'update' in request.POST and not updating:
				updatin = True
				update()
				updating = False

			elif 'cancel' in request.POST:
				cancelForm = CancelForm(request.POST)
				if cancelForm.is_valid():
					pk = cancelForm.cleaned_data['pk']
					f = Factura.objects.get(pk=pk)
					date = cancelForm.cleaned_data['cancel_date']
					cancelInvoice(f, date)
					make_payment_bill(f.path, [f.num], date)
					if cancelForm.cleaned_data['amount']:
						amount = int(
							form.cleaned_data['amount'].replace(".", ""))
						facturas = Factura.objects.filter(monto=amount,
						                                  pagada=False)
						context['facturas'] = facturas

			if form.cleaned_data['amount']:
				amount = int(form.cleaned_data['amount'].replace(".", ""))
				facturas = Factura.objects.filter(monto=amount, pagada=False)
				if form.cleaned_data['year']:
					facturas = facturas.filter(
						fecha__year=form.cleaned_data['year'])
					if form.cleaned_data['month']:
						facturas = facturas.filter(
							fecha__month=form.cleaned_data['month'])

				context['facturas'] = facturas

	context['form'] = form
	return HttpResponse(template.render(context, request))


def cancelInvoice(invoice, date):
	invoice.pagada = True
	invoice.fecha_cancelado = date
	path = invoice.path
	file = invoice.file
	new_dir = os.path.join(path, paid_dir)
	if not os.path.exists(new_dir):
		os.mkdir(new_dir)

	os.rename(os.path.join(path, file), os.path.join(new_dir, file))
	invoice.path = new_dir
	invoice.save()


def make_payment_bill(dir, nums, date):
	name = ""
	name += nums[0]
	if len(nums) > 1:
		for num in nums[1:]:
			name += ", " + num

	file = open(os.path.join(dir, name + ".txt"), "w+")
	amount = 0
	for num in nums:
		amount += Factura.objects.get(num=num).monto

	file.write("monto: {}, fecha: {}".format(amount, date))
	file.close()


def search_accum(request):
	global updating
	context = {}
	form = SearchForm()
	groups = []
	if request.method == "POST":
		if 'cancel-pk' in request.POST:
			nums = []
			date = datetime.datetime.strptime(request.POST['cancel_date'], '%m/%d/%Y')
			latestF = None
			for pk in request.POST.getlist('cancel-pk'):
				f = Factura.objects.get(pk=pk)
				cancelInvoice(f, date)
				nums.append(f.num)
				if latestF is None or latestF.fecha < f.fecha:
					latestF = f

			make_payment_bill(latestF.path, nums, date)

		if 'update' in request.POST and not updating:
			updatin = True
			update()
			updating = False

		else:
			form = SearchForm(request.POST)
			if form.is_valid() and form.cleaned_data['amount']:
				amount = int(form.cleaned_data['amount'] \
				             .replace(".", "").replace(",", ""))
				for client in Client.objects.all():
					facts = client.factura_set.filter(pagada=False,
					                                  monto__lte=amount)
					if form.cleaned_data['year']:
						facts = facts.filter(
							fecha__year=form.cleaned_data['year'])
						if form.cleaned_data['month']:
							facts = facts.filter(
								fecha__month=form.cleaned_data['month'])

					for i in range(1, 2 ** len(facts)):
						g = get_group(facts, i)
						val = 0
						for f in g:
							val += f.monto

						if val == amount:
							groups.append(g)

	context['form'] = form
	context['groups'] = groups
	template = loader.get_template('search_groups.html')
	return HttpResponse(template.render(context, request))


def get_group(facts, i):
	group = []
	n = 0
	while i > 0:
		if i & 1:
			group.append(facts[n])

		i = i >> 1
		n += 1

	return group


def update(root=''):
	new_dir = os.path.join(MEDIA_ROOT, root)
	for dir in os.listdir(new_dir):
		null_dir_list = ['OSORNO', 'anuladas', '00.2014',
		                 '00.2015', '00.2016', '00.2017', 'Thumbs.db',
		                 'install', '32_64']
		extn = dir.split('.')[-1]
		year = datetime.datetime.now().year
		if extn == 'msg' or extn == 'bmp' or extn == 'xlsx':
			continue

		if not (str(year) in dir or str(year - 1) in dir):
			continue

		if dir[-4:] == '.pdf':
			add_to_db(new_dir, dir, False)

		elif dir == paid_dir:
			add_paid(new_dir)

		elif os.path.isdir(new_dir):
			update(os.path.join(root, dir))


def add_paid(path):
	path = os.path.join(path, paid_dir)
	model_list = Factura.objects.filter(path__startswith=path).values_list(
		'file', flat=True)
	fact_list = os.listdir(path)
	for fact in fact_list:
		if fact not in model_list and fact[-4:] == '.pdf':
			add_to_db(path, fact, True)


def add_to_db(path, fact, paid):
	model_list = Factura.objects.filter(path__startswith=path).values_list(
		'file', flat=True)
	if fact in model_list:
		return

	rut = None
	newFact = None
	text = None
	try:
		pdf = PdfFileReader(open(path + '/' + fact, 'rb'))
		page = pdf.getPage(0)
		text = page.extractText()

		totalTag = 'TOTAL$'
		totalPos = text.find(totalTag)
		if totalPos == -1:
			totalTag = 'MontoTotal$\n'
			totalPos = text.find(totalTag)

		totalPos += len(totalTag)
		totalEnd = text[totalPos:totalPos + 20].find('\n') + totalPos
		if totalEnd == totalPos - 1:
			totalEnd = len(text)

		amount = int(text[totalPos:totalEnd].replace('.', ''))

		numTag = 'FACTURAELECTRONICA\nN°'
		numPos = text.find(numTag) + len(numTag)
		numEnd = text[numPos:numPos + 25].find('\n') + numPos
		if numPos == len(numTag) - 1:
			numTag = 'ELECTRONICANº'
			numPos = text.find(numTag) + len(numTag)
			numEnd = text[numPos:numPos + 25].find('S.') + numPos

		num = text[numPos:numEnd]
		clientTag = 'RUT:'
		clientPos = text.find(clientTag) + len(clientTag)
		if clientPos == len(clientTag) - 1:
			clientTag = 'R.U.T.:'
			clientPos = text.find(clientTag) + len(clientTag)
			clientEnd = text[clientPos:].find('-') + 3 + clientPos

		else:
			clientEnd = text[clientPos:clientPos + 25].find('\n') + clientPos

		clientRut = text[clientPos:clientEnd].replace(".", "").replace(' ', '')

		dateTag = 'Fecha:'
		dayPos = text.find(dateTag) + len(dateTag)
		if dayPos == len(dateTag) - 1:
			dateTag = 'Fecha Emision:'
			dayPos = text.find(dateTag) + len(dateTag)
			dayEnd = text[dayPos:dayPos + 30].find(' de ') + dayPos
			monthPos = dayEnd + 4
			monthEnd = text[monthPos:monthPos + 15].find(' del ') + monthPos
			yearPos = monthEnd + 5
			yearEnd = yearPos + 4

		else:
			dayEnd = text[dayPos:dayPos + 30].find('de') + dayPos
			monthPos = dayEnd + 2
			monthEnd = text[monthPos:monthPos + 15].find('de') + monthPos
			yearPos = monthEnd + 2
			yearEnd = yearPos + 4

		day = int(text[dayPos:dayEnd])
		month = text[monthPos:monthEnd]
		year = int(text[yearPos:yearEnd])

		monthConverter = {
			'Enero': 1,
			'Febrero': 2,
			'Marzo': 3,
			'Abril': 4,
			'Mayo': 5,
			'Junio': 6,
			'Julio': 7,
			'Agosto': 8,
			'Septiembre': 9,
			'Octubre': 10,
			'Noviembre': 11,
			'Diciembre': 12
		}

		monthNum = monthConverter[month]
		date = datetime.datetime(year, monthNum, day)
		newFact = Factura(num=num)
		newFact.path = path
		newFact.fecha = date
		newFact.file = fact
		newFact.monto = amount
		newFact.fecha_cancelado = datetime.datetime.now()
		newFact.pagada = paid
		dig, ver = clientRut.split("-")
		rut = Rut(dig, ver)

	except:
		print("error with file {}, dir {}".format(fact, path))

	try:
		newFact.client = Client.objects.get(rut__digits=rut.digits)

	except:
		if rut is None:
			print("error with file {}, dir {}".format(fact, path))
			return

		rut.save()
		newClient = Client(rut=rut)
		rsTag = 'RazónSocial:'
		rsPos = text.find(rsTag) + len(rsTag)
		rsEnd = text[rsPos:rsPos + 50].find('\n') + rsPos
		if rsPos == len(rsTag) - 1:
			rsTag = 'SEÑOR(ES):'
			rsPos = text.find(rsTag) + len(rsTag)
			rsEnd = text[rsPos:rsPos + 100].find('R.U.T.') + rsPos

		rs = text[rsPos:rsEnd]
		newClient.name = rs
		newClient.save()
		newFact.client = newClient

	try:
		newFact.save()
		print("{}, {}, {}".format(newFact.rut, newFact.num, newFact.monto))

	except:
		pass


def search_all(request):
	global updating
	form = SearchAllForm()
	template = loader.get_template('all.html')
	facts = Factura.objects.all()
	context = {}
	if request.method == "POST":
		if 'update' in request.POST and not updating:
			updatin = True
			update()
			updating = False

		form = SearchAllForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['amount']:
				try:
					facts = facts.filter(monto=form.cleaned_data['amount']
					                     .replace(".", "").replace(",", ""))
				except:
					pass

			if form.cleaned_data['fnum']:
				try:
					facts = facts.filter(num=form.cleaned_data['fnum'])
				except:
					pass

			if form.cleaned_data['client_rut']:
				try:
					dig, ver = form.cleaned_data['client_rut'] \
						.replace('.', '').split('-')
					facts = facts.filter(client__rut__digits=dig)
				except:
					pass

			if form.cleaned_data['date']:
				try:
					facts = facts.filter(fecha=form.cleaned_data['date'])
				except:
					pass

			if form.cleaned_data['date_cancelled']:
				try:
					facts = facts.filter(pagada=True,
					                     fecha_cancelado=form.cleaned_data[
						                     'date_cancelled'])
				except:
					pass

			if form.cleaned_data['paid']:
				try:
					paid = None
					if form.cleaned_data['paid'] == 'True':
						paid = True
					elif form.cleaned_data['paid'] == 'False':
						paid = False

					facts = facts.filter(pagada=paid)
				except:
					pass

			order = form.cleaned_data['order_by']
			facts = facts.order_by(order)

	context['form'] = form
	context['facts'] = facts
	return HttpResponse(template.render(context, request))
