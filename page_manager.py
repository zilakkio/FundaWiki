from datetime import datetime
import json
import re
import time
import uuid
from urllib.parse import quote

import utils


class PageManager:
    def __init__(self):
        self.pages = {"example": Page("example", "Example", "Example is this.", [], "admin")}

    def find_pages_with_link(self, link):
        keys = []
        for key, page in self.pages.items():
            if link in page.links:
                keys.append(key)
        return keys

    def get_page(self, title):
        return self.pages.get(title, None)

    def add_page(self, title, content, links, creator, is_axiomatic=False, is_admin=False):
        if title not in self.pages:
            self.pages[title.lower()] = Page(title.lower(), title, content, list(set(links)), creator,
                                             is_axiomatic=is_axiomatic and is_admin)
        else:
            self.update_page(title, content, links, creator, is_axiomatic=is_axiomatic and is_admin)

    def update_page(self, title, new_content, new_links, creator, is_axiomatic=False, admin=False, version_id=None):
        if title in self.pages:
            page = self.pages[title]
            links = list(set(new_links))
            version = page.versions.get(version_id)
            if creator == version.creator:
                if version:
                    version.content = new_content
                    version.links = links
                    version.creation_time = time.time()
                    version.is_axiomatic = is_axiomatic
            else:
                for ver in [v for v, ver in page.versions.items() if ver.creator == creator]:
                    page.versions.pop(ver)
                version = Version(page.key, new_content, links, creator, creation_time=time.time(),
                                  is_axiomatic=is_axiomatic)
                if page.is_verified:
                    page.versions = {version.id: version}
                else:
                    page.add_version(version)

    def get_all_pages(self):
        return [i for i in self.pages.values()]

    def search_pages(self, query):
        return [page.title for page in self.pages.values() if query.lower() in page.key]

    def to_json(self):
        pages_data = {title: page.to_json() for title, page in self.pages.items()}
        return json.dumps(pages_data)

    @staticmethod
    def from_json(json_data):
        data = json.loads(json_data)
        page_manager = PageManager()
        page_manager.pages = {title: Page.from_json(page_json) for title, page_json in data.items()}
        return page_manager

    def save(self):
        jsons = self.to_json()
        with open("funda.json", "w") as file:
            file.write(jsons)

    @staticmethod
    def load():
        with open("funda.json", "r") as file:
            return PageManager.from_json(file.read())


class Version:
    def __init__(self, page_id, content, links, creator,
                 creation_time=None, is_axiomatic=False):
        self.page_id = page_id
        self.id = str(uuid.uuid4())

        self.content = content
        self.links: list[str] = links

        self.creator = creator
        self.creation_time = creation_time or time.time()
        self.is_axiomatic = is_axiomatic

        self.has_new_links = True
        self.links_from = []

        self.rendered = self.content

    @property
    def datetime(self):
        date_time = datetime.utcfromtimestamp(self.creation_time)
        formatted_date = date_time.strftime("%d.%m.%Y (%H:%M:%S)")
        return formatted_date

    @property
    def is_strict(self):
        if self.is_axiomatic:
            return True
        return not self.has_new_links and all([pm.pages.get(unit).primary.is_strict for unit in self.links_from])

    @property
    def all_links(self):
        return [self.page_id] + self.links

    def render_content(self, pm: PageManager):
        has_new_links = False
        links_from = []

        if self.is_axiomatic:
            self.rendered = self.content
            return self.content, True

        def create_link(text, key):
            if pm.pages.get(key).primary.is_strict:
                return f'<a href="/define/{quote(key)}">{text}</a>'
            else:
                return f'<a href="/define/{quote(key)}" style="color:orange;">{text}</a>'

        def create_new_link(text, key):
            nonlocal has_new_links
            has_new_links = True
            return f'<a href="/create/{quote(key)}" style="color:red;">{text}</a>'

        def create_conflict_link(text, link):
            return f'<a href="/conflict/{quote(link)}" style="color:orange;">{text}</a>'

        def bold_text(text):
            return f'<b>{text}</b>'

        def create_any_link(text, link, is_fish=False):
            link = link.lower()

            if link in self.all_links and not is_fish:
                return bold_text(text)

            pages = pm.find_pages_with_link(link)

            if len(pages) == 1:
                links_from.append(pages[0])
                return create_link(text, pages[0])
            elif not pages:
                links_from.append(link)
                return create_new_link(text, link)
            else:
                links_from.append(link)
                return create_conflict_link(text, link)

        units = []
        tokens = utils.tokenize(self.content)

        for token in tokens:
            if token == " ":
                units.append(token)
            elif token.startswith('[') and token.endswith(']'):
                token = token[1:-1]
                if "::" in token:
                    before, after = token.split("::")
                    units.append(create_any_link(before, after, is_fish=True))
                else:
                    units.append(create_any_link(token, token))
            else:
                units.append(create_any_link(token, token))

        self.rendered = ''.join(units)
        self.has_new_links = has_new_links
        self.links_from = links_from

    def to_json(self):
        # Convert the object to a dictionary
        version_dict = {
            'page_id': self.page_id,
            'id': self.id,
            'content': self.content,
            'links': self.links,
            'creator': self.creator,
            'creation_time': self.creation_time,
            'is_axiomatic': self.is_axiomatic,
        }
        return json.dumps(version_dict)

    @staticmethod
    def from_json(json_str):
        # Load the dictionary from JSON string
        obj = json.loads(json_str)
        # Create a new Version object
        version = Version(obj['page_id'], obj['content'], obj['links'], obj['creator'], obj['creation_time'],
                          is_axiomatic=obj['is_axiomatic'])
        version.id = obj['id']
        return version


class Page:
    def __init__(self, key, title, content, links, creator,
                 creation_time=None, is_axiomatic=False, from_obj=False):
        self.key = key
        self.title = title
        self.is_verified = False
        self.versions = {}
        if not from_obj:
            self.add_version(Version(self.key, content, links, creator,
                                     creation_time=creation_time, is_axiomatic=is_axiomatic))

    @property
    def links(self):
        return [self.key] + self.primary.links

    @property
    def primary(self):
        return self.get_versions_sorted_by_upvotes()[0]

    def add_version(self, version):
        self.versions = {version.id: version} | self.versions

    def get_versions_sorted_by_upvotes(self):
        return sorted(self.versions.values(), key=lambda v: v.creation_time, reverse=True)

    def to_json(self):
        # Convert the object and its versions to a dictionary
        # print(self.versions)
        page_dict = {
            'key': self.key,
            'is_verified': self.is_verified,
            'title': self.title,
            'versions': {vid: version.to_json() for vid, version in self.versions.items()}
        }
        return json.dumps(page_dict)

    @staticmethod
    def from_json(json_str):
        page_dict = json.loads(json_str)
        page = Page(page_dict['key'], page_dict['title'], '', [], '', from_obj=True)
        page.is_verified = page_dict['is_verified']
        # Add versions
        for vid, version_str in page_dict['versions'].items():
            version = Version.from_json(version_str)
            page.versions[vid] = version
        return page


pm = PageManager.load()
