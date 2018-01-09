#!/usr/bin/env python
import re
import datetime
from hashlib import md5

import requests
from lxml import html

skeleton_headers = {
    'Accept': 'image/gif, image/jpeg, image/pjpeg, application/x-ms-application, application/xaml+xml, \
application/x-ms-xbap, */*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/7.0)'  # 伪装成Windows 7 IE 11（兼容性视图）
}

LOGIN_URL = 'http://passport-yun.szsy.cn/login?service=http://gzb.szsy.cn/card/Default.aspx'
CARD_SYSTEM_LOGIN_URL = 'http://gzb.szsy.cn/card/'
CALENDAR_URL = 'http://gzb.szsy.cn/card/Restaurant/RestaurantUserMenu/RestaurantUserSelect.aspx'
MENU_URL = 'http://gzb.szsy.cn/card/Restaurant/RestaurantUserMenu/RestaurantUserMenu.aspx'

MEAL_NAME = ('早餐', '午餐', '晚餐')

post_login_skeleton_form = {
    '__EVENTARGUMENT': '',
    '__LASTFOCUS': ''
}


class SessionExpired(Exception):
    def __str__(self):
        return "Your session has expired."


class Session(requests.Session):
    def __init__(self, cookies):
        """:type cookies: dict"""
        super().__init__()
        self.cookies = requests.utils.cookiejar_from_dict(cookies)

    def s_get(self, url, params=None, referrer=None, logged_in=True):
        """
        自制的session.get
        :type url: str
        :type params: dict
        :type referrer: str
        :type logged_in: bool
        :rtype: requests.Response
        """
        self.headers = skeleton_headers.copy()
        if referrer is not None:
            self.headers['Referer'] = referrer
        request = super().get(url, params=params)

        # 会话过期后，服务器发送302将用户重定向到登录页，service的值为目标地址
        if 'http://passport-yun.szsy.cn/login?service=' in request.url and logged_in:
            raise SessionExpired
        return request

    def s_post(self, url, data, params=None, referrer=None, logged_in=True):
        """
        :type url: str
        :type data: dict
        :type params: dict
        :type referrer: str
        :type logged_in: bool
        :rtype: requests.Response
        """
        self.headers = skeleton_headers.copy()
        if referrer is not None:
            self.headers['Referer'] = referrer
        if logged_in:
            real_data = post_login_skeleton_form.copy()
            real_data.update(data)
        else:
            real_data = data
        request = super().post(url, real_data, params=params)

        if LOGIN_URL in request.url and logged_in:
            raise SessionExpired
        return request

    def extract_cookies(self):
        """:rtype: dict"""
        return requests.utils.dict_from_cookiejar(self.cookies)


class Login(object):
    def __init__(self, cookies):
        self.session = Session(cookies)

    def login_cas(self, username, password, cas_param=None):
        """
        教务系统使用CAS中央登陆，本实现以返回的页面是否存在“认证信息无效。”判断是否登录成功
        若成功，返回姓名和账户余额
        若失败，返回重新登陆需要的[lt, execution]
        :type username: str
        :type password: str
        :type cas_param: list
        :param username: 用户名
        :param password: 密码
        :param cas_param: 上次登录返回的[lt, execution]
        :rtype: (bool, list[str])
        """
        if cas_param is None:
            # 首次访问，须获取页面表单中CAS登录需要的参数
            login_page = self.session.s_get(LOGIN_URL, logged_in=False)
            lt = re.search('name="lt" value="(.*?)"', login_page.text).group(1)
            execution = re.search('name="execution" value="(.*?)"', login_page.text).group(1)
        else:
            lt = cas_param[0]
            execution = cas_param[1]

        login_form = {
            'username': username,
            'password': md5(password.encode('utf-8')).hexdigest(),
            'lt': lt,
            'execution': execution,
            '_eventId': 'submit'
        }
        auth = self.session.s_post(LOGIN_URL, login_form, referrer=LOGIN_URL, logged_in=False)
        auth_status = '认证信息无效。' in auth.text

        if auth_status:
            # 存下本次失败登录返回的CAS参数，供下次使用
            lt = re.search('name="lt" value="(.*?)"', auth.text).group(1)
            execution = re.search('name="execution" value="(.*?)"', auth.text).group(1)
            return auth_status, [lt, execution]

        name = re.search(r'<span id="LblUserName">当前用户：(.*?)</span>', auth.text).group(1)
        balance = re.search(r'<span id="LblBalance">帐户余额：(.*?)元</span>', auth.text).group(1)

        return auth_status, [name, balance]

    def canteen_logout(self):
        """进行退出，此处直接进行CAS退出，没有先进行教务系统的退出（因为懒）"""
        self.session.s_get('http://passport-yun.szsy.cn/logout', referrer='http://gzb.szsy.cn/card/Default.aspx', logged_in=False)
        del self.session


def _get_web_forms_field(page):
    """
    从页面中得到ASP.NET Web Forms的View State, View State Generator, Event Validation
    [viewstate, viewstategenertor, eventvalidation]
    :type page: str
    :rtype: list
    """
    vs = re.search(r'id="__VIEWSTATE" value="(.*?)"', page).group(1)
    vsg = re.search(r'id="__VIEWSTATEGENERATOR" value="(.*?)"', page).group(1)
    ev = re.search(r'id="__EVENTVALIDATION" value="(.*?)"', page).group(1)
    return [vs, vsg, ev]


def _parse_date_list(page):
    """
    用来解析选择日期的页面，得到可查询的日期的列表
    :type page: str
    :rtype: list
    """
    date_list = re.findall(r'\?Date=(\d{4}-\d{2}-\d{2})', page)

    return date_list


class Calendar(dict):
    def __init__(self, selected, selectable_year, init_dict, form_param=None, cookies=None):
        """
        :type selected: list[int]
        :type form_param: list[str] or NoneType
        :type selectable_year: list[str]
        :type init_dict: dict[str, str]
        :type cookies: dict or NoneType
        :param selected: [选中的年份, 选中的月份]
        :param selectable_year: [可选的年份]
        """
        super().__init__()
        self.selected_year, self.selected_month = selected
        self.form_param = form_param

        self.selectable_year = selectable_year

        self.update(init_dict)
        self.cookies = cookies

    @classmethod
    def calendar_init(cls, session):
        """
        第一次访问选择日期的页面
        我决定在登录后直接初始化菜单，以利用登录“一卡通”系统时的Session，减少等待时间
        :type session: Session
        """
        calendar = session.s_get(CALENDAR_URL, referrer='http://gzb.szsy.cn/card/Default.aspx')
        page = calendar.text
        form_param = _get_web_forms_field(page)
        selectable_year = [int(year) for year in re.findall(r'value="(\d{4})"', page)]
        selectable_year.sort()
        selected_year = re.search(r'<option selected="selected" value="\d{4}">(\d{4})</option>', page).group(1)
        selected_month = re.search(r'<option selected="selected" value="\d{1,2}">(\d{1,2})月</option>', page).group(
            1).zfill(2)
        date_string = selected_year + '-' + selected_month
        init_dict = {date_string: _parse_date_list(page)}
        return cls([int(selected_year), int(selected_month)], selectable_year, init_dict, form_param,
                   session.extract_cookies())

    def query_calendar(self, year, month):
        """
        查询对应月份的菜单
        :type year: int
        :type month: int
        :param year: 菜单的年份
        :param month: 菜单的月份
        """
        session = Session(self.cookies)
        query_calendar_form = {
            '__EVENTTARGET': 'DrplstMonth1$DrplstControl',
            '__VIEWSTATE': self.form_param[0],
            '__VIEWSTATEGENERATOR': self.form_param[1],
            '__EVENTVALIDATION': self.form_param[2],
            'DrplstYear1$DrplstControl': year,
            'DrplstMonth1$DrplstControl': month
        }
        post_calendar = session.s_post(CALENDAR_URL, query_calendar_form, referrer=CALENDAR_URL)
        page = post_calendar.text
        self.form_param = _get_web_forms_field(page)

        if not year == self.selected_year:
            # 切换年份时，需要像处理不订餐那么搞
            query_calendar_form.update({
                '__VIEWSTATE': self.form_param[0],
                '__VIEWSTATEGENERATOR': self.form_param[1],
                '__EVENTVALIDATION': self.form_param[2]
            })
            post_calendar = session.s_post(CALENDAR_URL, query_calendar_form, referrer=CALENDAR_URL)
            page = post_calendar.text
            self.form_param = _get_web_forms_field(page)
            self.selected_year = year

        self.cookies = session.extract_cookies()
        return _parse_date_list(page)

    def test(self, year, month):
        """
        尽管在初始化Calendar这个类的时候已经指定了year和month，我还是再传一次参。我清楚这逻辑很奇怪。
        :type year: int
        :type month: int
        :param year: 要查询菜单的年份
        :param month: 要查询菜单的月份
        """
        query_string = str(year) + '-' + str(month).zfill(2)
        if query_string not in self:
            self[query_string] = self.query_calendar(year, month)
        # 若年份不同，query_calendar()会更新self.selected_year
        self.selected_month = month

    def current(self):
        """
        :return: 选定月份的日期列表
        :rtype: list[int]
        """
        current = self[str(self.selected_year) + '-' + str(self.selected_month).zfill(2)]
        new = [datetime.datetime.strptime(date, '%Y-%m-%d').date() for date in current]
        return new

    @staticmethod
    def orderable_day():
        return datetime.timedelta(3 + 1) + datetime.date.today()


def get_course_count(page, menu_sequence):
    """
    :type page: str
    :type menu_sequence: int
    :param menu_sequence: 这一餐的序号
    :rtype: int
    """
    return len(re.findall(r'Repeater1_GvReport_{0}_LblMaxno_\d'.format(menu_sequence), page))


class Course(object):
    def __init__(self, seq, course):
        self.id = seq
        self.num = int(course[0])
        self.type = course[1]
        self.name = course[2]
        self.price = float(course[5])
        self.max = int(course[6])
        self.current = int(course[7])
        self.iter = range(self.max + 1)


class Meal(list):
    def __init__(self, seq, menu_list, course_count):
        super().__init__()
        self.required_course = []
        self.id = seq
        self.name = MEAL_NAME[self.id]

        for course_seq in range(course_count):
            start = 9 * course_seq
            end = 9 * (course_seq + 1)
            l = menu_list[start:end]
            # 用于记录必选菜的编号，以处理必选菜不在最后的特殊情况
            if l[4] == '必选':
                self.required_course.append(course_seq)
            self.append(Course(course_seq, l))


class Menu(list):
    def __init__(self, date, cookies):
        super().__init__()
        self.session = Session(cookies)
        page = self.get_menu(date)
        self.form_param = _get_web_forms_field(page)
        # 只有装着菜单的table是带"id"属性的
        meal_count = len(re.findall(r'id="Repeater1_GvReport_(\d)"', page))
        self.do_not_order = [int(x) for x in
                             re.findall(r'name="Repeater1\$ctl0(\d)\$CbkMealtimes" checked="checked"', page)]

        if '<a onclick="return subs();"' in page:
            self.mutable = True
        elif '<a onclick="return msg();"' or meal_count == 0 in page:
            self.mutable = False

        tree = html.fromstring(page)
        for meal_seq in range(meal_count):
            # 尽管没遇到过菜数不是9的情况，但还是别把它写死吧
            course_count = get_course_count(page, meal_seq)
            # 若菜单不可修改，总价那一行不会有那个id标签
            if not self.mutable:
                course_count -= 1
            xpath = '//table[@id="Repeater1_GvReport_{0}"]/tr/td//text()'.format(meal_seq)
            menu_item = tree.xpath(xpath)
            self.append(Meal(meal_seq, menu_item, course_count))

    def get_course_amount(self):
        """
        参数为菜单。返回值为菜单中已订菜的数量的字典
        :rtype: dict
        """
        course_amount = {}
        for meal in self:
            for course in meal:
                # (餐次, 编号) = 数量
                course_amount[meal.id, course.id] = course.current

        return course_amount

    def get_menu(self, date):
        """
        获得给定日期的菜单，返回菜单的页面
        :type date: str
        :rtype: str
        """
        menu = self.session.s_get(MENU_URL, params={'Date': date}, referrer=CALENDAR_URL)

        # 我也是被逼的……如果不这么干，lxml提取出的列表里会有那串空白
        # 且看上去remove_blank_text不是这么用的
        page = re.sub(r'\r\n {24}(?: {4})?', '', menu.text)
        return page


def gen_menu_param(course_amount):
    """
    参数为course_amount这个dict，返回值为CALLBACKPARAM
    :type course_amount: dict
    :rtype: str
    """
    param_string = ''
    for k, v in course_amount.items():
        # {0}用于和自己拼在一起。{1[0]}为key中的第一个数，即meal_order，{1[1]}即course
        param_string = '{0}Repeater1_GvReport_{1[0]}_TxtNum_{1[2]}@{2}|'.format(
            param_string, k, v
        )

    return param_string


def submit_menu(date, course_amount, do_not_order, form_param, cookies):
    """
    返回是否成功的Bool
    :type date: str
    :type course_amount: dict
    :type do_not_order: list
    :type form_param: list
    :type cookies: dict
    :param date: 提交菜单的日期
    :param course_amount: 菜的数量
    :param do_not_order: [原页面已勾选“不订餐”的餐次, 要“不订餐”的餐次, 要取消“不订餐”的餐次]
    :param form_param: 菜单页与ASP.NET Web Forms相关的字段
    :rtype: bool
    """
    session = Session(cookies)
    # unpack
    do_not_order_list, to_select, to_deselect = do_not_order
    submit_menu_form = {
        '__VIEWSTATE': form_param[0],
        '__VIEWSTATEGENERATOR': form_param[1],
        '__VIEWSTATEENCRYPTED': '',
        'DrplstRestaurantBasis1$DrplstControl': '4d05282b-b96f-4a3f-ba54-fc218266a524',
        '__EVENTVALIDATION': form_param[2]
    }

    # 把原页面已勾选“不订餐”的放入表单
    for meal_order in do_not_order_list:
        box_id = 'Repeater1$ctl0{0}$CbkMealtimes'.format(meal_order)
        submit_menu_form[box_id] = 'on'

    # 用来模拟浏览器的做法，提交“不订餐”的变化
    # 要一个一个加，一个一个减
    if to_select + to_deselect:
        for meal_order in to_select + to_deselect:
            box_id = 'Repeater1$ctl0{0}$CbkMealtimes'.format(meal_order)

            if meal_order in to_select:
                submit_menu_form[box_id] = 'on'
            elif meal_order in to_deselect:
                del submit_menu_form[box_id]

            submit_menu_form['__EVENTTARGET'] = box_id
            submit_do_not_order = session.s_post(
                MENU_URL,
                submit_menu_form,
                params={'Date': date},
                referrer=MENU_URL + '?Date=' + date
            )
            submit_return_page = submit_do_not_order.text

            # 提交后会返回新页面，又要改这些
            # Evil ASP.NET!
            form_param = _get_web_forms_field(submit_return_page)
            submit_menu_form.update({
                '__VIEWSTATE': form_param[0],
                '__VIEWSTATEGENERATOR': form_param[1],
                '__EVENTVALIDATION': form_param[2]
            })

    # 提交菜单
    menu_param = gen_menu_param(course_amount)
    submit_menu_form.update({
        '__EVENTTARGET': '',
        '__CALLBACKID': '__Page',
        '__CALLBACKPARAM': menu_param
    })

    post_menu = session.s_post(
        MENU_URL,
        submit_menu_form,
        params={'Date': date},
        referrer=MENU_URL + '?Date=' + date
    )
    status = '订餐成功！' in post_menu.text

    return status
