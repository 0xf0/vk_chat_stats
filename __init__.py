# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import math
import string
import sqlite3
import requests
import collections
from lxml import html
from urllib.parse import urlencode
from betterprint import pformat

login = ""
password = ""
app_id = 6356270 
scope = 2+4096+65536  # https://vk.com/dev/permissions
token_file = '.token'
db_file = 'db.sqlite3'
chat_id = 2000000015
opts = {
	"print_last_online": True,
	"print_top_words": True,
	"top_words_max": 25,
	"user_posts_counter": True,
	"user_posts_max": 25
}

session = requests.Session()
token = False
db = sqlite3.connect(db_file)
cur = db.cursor()


class API(object):
	__slots__ = ("__token", "__version", "__method")
	def __init__(self, token=None, version='5.60', **kwargs):
		self.__token = token
		self.__version = version
		self.__method = kwargs.get('method', '')
	def get_url(self, method=None, **kwargs):
		kwargs.setdefault('v', self.__version)
		if self.__token is not None:
			kwargs.setdefault('access_token', self.__token)
		return 'https://api.vk.com/method/{}?{}'.format(method or self.__method, urlencode(kwargs))
	def request(self, method, **kwargs):
		kwargs.setdefault('v', self.__version)
		if self.__token is not None:
			kwargs.setdefault('access_token', self.__token)
		r = requests.get(self.get_url(method, **kwargs))
		time.sleep(.4)
		return r
	def __getattr__(self, attr):
		method = ('{}.{}'.format(self.__method, attr)).lstrip('.')
		return API(self.__token, version=self.__version, method=method)
	def __call__(self, **kwargs):
		return self.request(self.__method, **kwargs)
	def get_conversations(self, answer):
		values = {}
		if "response" in answer and "items" in answer["response"]:
			for item in answer["response"]["items"]:
				if item['conversation']['peer']['type'] == "chat":
					peer_id = item['conversation']['peer']['id']
					local_id = item['conversation']['peer']['local_id']
					title = item['conversation']['chat_settings']['title']
					values[peer_id] = {"lid": local_id, "title": title}
		return values



def doc(_html):
	try:
		return html.fromstring(_html)
	except Exception as e:
		print("doc exception: {}".format(e))
		return None


def req(url, post=False):
	global session
	try:
		if not isinstance(post, dict):
			r = session.get(url)
		else:
			r = session.post(url, data=post)
		if r:
			r.encoding = 'utf-8'
			try:
				setattr(r, "doc", doc(r.text))
			except Exception as e:
				print("cant set doc attr")
			return r
		else:
			print("request failed, no data")
	except Exception as e:
		print("request failed: {}".format(e))
		return False


def read_token():
	global token
	try:
		if os.path.isfile(token_file):
			with open(token_file, 'r') as f:
				token = f.read().strip()
			return True
		else:
			print("no token file")
	except Exception as e:
		print("whoops: {}".format(e))
	return False



def write_token():
	try:
		with open(token_file, 'w') as f:
			f.write(token)
			return True
	except Exception as e:
		print("whoops: {}".format(e))
		return False


def get_token():
	global token, session
	try:
		r = req("https://oauth.vk.com/authorize?client_id={}&scope={}&redirect_uri=http://oauth.vk.com/blank.html&display=wap&response_type=token".format(app_id, scope))
	except Exception as e:
		print("whoops: {}".format(e))
		return False
	post = {}
	if r.doc is not None:
		try:
			action = r.doc.xpath("//form")[0].get("action")
		except Exception as e:
			print("no action: {}".format(e))
			return False
		try:
			post["ip_h"] = r.doc.xpath("//form/input[@name='ip_h']")[0].get("value")
		except Exception as e:
			print("no ip_h: {}".format(e))
			return False
		try:
			post["lg_h"] = r.doc.xpath("//form/input[@name='lg_h']")[0].get("value")
		except Exception as e:
			print("no lg_h: {}".format(e))
			return False
		try:
			post["to"] = r.doc.xpath("//form/input[@name='to']")[0].get("value")
		except Exception as e:
			print("no to: {}".format(e))
			return False
		post["_origin"] = "https://oauth.vk.com"
		post["email"] = login
		post["pass"] = password
		r = req(url="{}".format(action), post=post)
		if r:
			if 'access_token' in r.url:
				try:
					token = re.search(r'access_token=([^&]+)', r.url).group(1)
				except Exception as e:
					print("failed to find token: {}".format(e))
			else:
				print("no access_token in url: {}".format(r.url))
		else:
			print("failed to post access_token request")
			return False
	else:
		print("no doc")
		return False


def platform(num):
	platforms = {1: 'мобильной версии', 2: 'приложения для iPhone', 3: 'приложения для iPad', 4: 'приложения для Android', 5: 'приложения для Windows Phone',
					6: 'приложения для Windows 10', 7: 'полной версии сайта', 8: 'VK Mobile'}
	return platforms[num] if num in platforms else "unk"


def was(sex):
	lst = {1: "была", 2: "был"}
	return lst[sex] if sex in lst else "было"



def print_last_online(lst):
	for dick_id, dick_data in lst.items():
		print("{} последний раз {} {} с {}".format(dick_data['name'], was(dick_data['sex']), dick_data['time'], platform(dick_data['platform'])))


def special_characters(data):
    regexp = '[{}]*'.format(string.punctuation)
    return re.sub(regexp, '', data)


def plural(val, vals):
	if val == 0:
		return vals[val]
	n = abs(val % 100)
	n1 = n % 10
	if n > 10 and n < 20:
		return vals[1]
	if n1 > 1 and n1 < 5:
		return vals[2]
	if n1 == 1:
		return vals[3]
	return vals[1]


def main():
	global token
	if not read_token():
		get_token()
		if not token:
			print("no token")
			sys.exit(1)
		else:
			if not write_token():
				print("failed to write token")
			else:
				print("wrote token to the file")
	else:
		print("token ok")
	vk = API(token=token, version='5.80')
	conv = vk.messages.getConversations(offset=0, count=200, extended=1).json()
	conv = vk.get_conversations(conv)
	if chat_id in conv:
		conv = conv[chat_id]
		chat_info = vk.messages.getChat(chat_id=conv["lid"], fields="last_seen,sex").json()
		if opts["print_last_online"]:
			last_seen = {}
		for dick in chat_info['response']['users']:
			local_time = time.localtime(dick['last_seen']['time'])
			last_seen[dick['id']] = {
				"name": "{} {}".format(dick['first_name'], dick['last_name']),
				"time": "{}".format(time.strftime("%d.%m %H:%M:%S", local_time)),
				"platform": dick['last_seen']['platform'],
				"invited_by": dick['invited_by'],
				"sex": dick["sex"]
			}
		if opts["print_last_online"]:
			print_last_online(last_seen)
		if opts["print_top_words"]:
			db_msg_ids = []
			cur.execute("CREATE TABLE IF NOT EXISTS conversations(peer_id INTEGER PRIMARY KEY ASC, id INTEGER, text TEXT, date TEXT, from_id INTEGER)")
			db.commit()
			for row in cur.execute('SELECT id FROM conversations WHERE peer_id = ?', (chat_id,)):
				db_msg_ids.append(row[0])
			messages_info = vk.messages.getHistory(offset=0, count=1, peer_id=chat_id).json()
			messages_count = messages_info['response']['count']
			del messages_info
			offset = len(db_msg_ids)
			while offset < messages_count:
				try:
					print("offset {} of {}".format(offset, messages_count))
					messages = vk.messages.getHistory(offset=offset, count=200, peer_id=chat_id).json()
					offset += 200
					for message in messages['response']['items']:
						try:
							if message['id'] not in db_msg_ids:
								db_msg_ids.append(message['id'])
								dt = "{}".format(time.strftime("%d.%m %H:%M:%S", time.localtime(message['date'])))
								cur.execute("INSERT INTO conversations(peer_id, id, text, date, from_id) VALUES(?, ?, ?, ?, ?)",
									(chat_id, message['id'], message['text'], dt, message['from_id']))
								db.commit()
						except Exception as e:
							print("whoops: {}".format(e))
				except Exception as e:
					print("whoops: {}".format(e))
			words_counter = collections.Counter()
			if opts["user_posts_counter"]:
				user_posts_counter = collections.Counter()
			for row in cur.execute('SELECT text, from_id FROM conversations WHERE peer_id = ? AND text != ?', (chat_id, '')):
				if opts["user_posts_counter"]:
					user_posts_counter[row[1]] += 1
				for word in special_characters(row[0]).split():
					if len(word) < 3:
						continue
					words_counter[word] += 1
			print("Топ {} слов".format(opts["top_words_max"]))
			i = 1
			for word in words_counter.most_common(opts["top_words_max"]):
				print("{:<2}) {} [{} {}]".format(i, word[0], word[1], plural(word[1], {1: "раз", 2: "раза", 3: "раз"})))
				i += 1
			if opts["user_posts_counter"]:
				print("Топ {} юзеров:")
				i = 1
				for dick in user_posts_counter.most_common(opts["user_posts_max"]):
					print("{:<2}) {} [{} {}]".format(i, row[1], word[1], plural(word[1], {1: "сообщений", 2: "сообщения", 3: "сообщений"})))
					i += 1

if __name__ == "__main__":
	main()