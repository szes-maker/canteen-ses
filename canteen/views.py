from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .canteen_utils import *


def login_required(request, login_url='/login/'):
    pass


def homepage(request):
    if request.session.get('id', False):
        if request.method == 'POST':
            year = request.POST.get('year', '')
            month = request.POST.get('month', '')
            return HttpResponseRedirect(reverse('query', kwargs={'year': year, 'month': month}))
        else:
            selected = request.session.get('calendar_selected', None)
            selectable_year = request.session.get('selectable_year', None)
            calendar_dict = request.session.get('calendar_dict', None)
            calendar = Calendar(selected, selectable_year, calendar_dict)

            context = {
                'calendar': calendar,
                'month_list': range(1, 13),
                'name': request.session['name'],
                'balance': request.session['balance']
            }
            return render(request, 'canteen/homepage.html', context=context)
    else:
        return HttpResponseRedirect('/login/')


def query(request, year, month):
    if request.session.get('id', False):
        year, month = int(year), int(month)

        cookies = request.session.get('cookies', None)
        form_param = request.session.get('calendar_form_param', None)
        selectable_year = request.session.get('selectable_year', None)
        selected = request.session.get('calendar_selected', None)
        init_dict = request.session.get('calendar_dict', None)
        calendar = Calendar(selected, selectable_year, init_dict, form_param, cookies)

        try:
            calendar.test(year, month)
        except SessionExpired:
            request.session.flush()
            return HttpResponseRedirect('/login/?next={}'.format(request.path))
        cookies = calendar.cookies
        context = {
            'calendar': calendar,
            'month_list': range(1, 13),
            'name': request.session['name'],
            'balance': request.session['balance'],
            'id': request.session['id']
        }
        request.session.update({
            'cookies': cookies,
            'calendar_form_param': calendar.form_param,
            'calendar_dict': calendar,
            'calendar_selected': [calendar.selected_year, calendar.selected_month]
        })
        return render(request, 'canteen/query.html', context=context)
    else:
        return HttpResponseRedirect('/login/?next={}'.format(request.path))


def menu(request, year, month, day):
    if request.session.get('id', False):
        cookies = request.session.get('cookies', None)
        # 统一宽度。这样就能够处理2015-9-3这种“格式错误”的日期了
        date = '{0}-{1}-{2}'.format(
            year.zfill(4),
            month.zfill(2),
            day.zfill(2)
        )

        try:
            menu_helper = Menu(date, cookies)
        except SessionExpired:
            request.session.flush()
            return HttpResponseRedirect('/login/?next={}'.format(request.path))

        request.session.update({
            'cookies': menu_helper.session.extract_cookies(),
            'form_param_' + date: menu_helper.form_param,
            'not_order_' + date: menu_helper.do_not_order
        })
        context = {
            'name': request.session['name'],
            'year': year,
            'month': month,
            'day': day,
            'menu': menu_helper,
            'balance': request.session['balance']
        }
        return render(request, 'canteen/menu.html', context)
    else:
        return HttpResponseRedirect('/login/?next={}'.format(request.path))


def submit(request, year, month, day):
    if request.session.get('id', False):
        if request.method == 'POST':
            # 统一宽度。这样就能够处理2015-9-3这种“格式错误”的日期了
            date = '{0}-{1}-{2}'.format(
                year.zfill(4),
                month.zfill(2),
                day.zfill(2)
            )
            cookies = request.session.get('cookies', None)
            form_param = request.session.get('form_param_' + date, None)
            do_not_order_original = set(request.session.get('not_order_' + date, None))

            cleaned_post = request.POST.copy()
            del cleaned_post['csrfmiddlewaretoken']

            do_not_order_current = set()
            for key in list(cleaned_post.keys()):
                if key[0] == 'd':
                    do_not_order_current.add(int(key[1]))
                    del cleaned_post[key]

            to_add = list(do_not_order_current - do_not_order_original)
            to_remove = list(do_not_order_original - do_not_order_current)
            do_not_order = [do_not_order_original, to_add, to_remove]

            status = submit_menu(date, cleaned_post, do_not_order, form_param, cookies)

            selectable_year = request.session.get('selectable_year', None)
            selected = request.session.get('calendar_selected', None)
            init_dict = request.session.get('calendar_dict', None)
            calendar = Calendar(selected, selectable_year, init_dict)

            context = {
                'name': request.session['name'],
                'balance': request.session['balance'],
                'result': status,
                'month_list': range(1, 13),
                'calendar': calendar
            }
            return render(request, 'canteen/result.html', context)
        else:
            return HttpResponseRedirect('/menu/{0}/{1}/{2}/'.format(year, month, day))
    else:
        return HttpResponseRedirect('/login/')


def login(request):
    if request.method == 'POST' and not request.session.get('id', False):
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        # 用于处理登录失败
        cas_param = request.session.get('cas_param', None)
        cookies = request.session.get('cookies', None)

        login_helper = Login(cookies)
        auth_status, payload = login_helper.login_cas(username, password, cas_param)

        if auth_status:
            # 用于清理
            try:
                del request.session['cas_param']
            except KeyError:
                pass

            name, balance = login_helper.login_card_system()
            calendar = Calendar.calendar_init(login_helper.session)
            cookies = calendar.cookies
            request.session.update({
                'id': username,
                'name': name,
                'balance': balance,
                'calendar_form_param': calendar.form_param,
                'calendar_dict': calendar,
                'selectable_year': calendar.selectable_year,
                'calendar_selected': [calendar.selected_year, calendar.selected_month]
            })
        else:
            request.session['cas_param'] = payload
            cookies = login_helper.session.extract_cookies()

        request.session['cookies'] = cookies
    else:
        request.session['url'] = request.GET.get('next', '/')

    if request.session.get('id', False):
        return HttpResponseRedirect(request.session['url'])
    else:
        return render(request, 'canteen/login.html')


def logout(request):
    cookies = request.session.get('cookies', False)
    if cookies:
        login_helper = Login(cookies)
        login_helper.canteen_logout()
        request.session.flush()

    return HttpResponseRedirect('/login/')
