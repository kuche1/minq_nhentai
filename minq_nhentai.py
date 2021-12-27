#! /usr/bin/env python3

# TODO
# check for internet connection
# fetch tags from https://nhentai.net/tags/
# implement caching
# implement normal menu mechanism
# use viu [update PKGBUILD]
# include recommended hentai
# automatically download hole hentai
# cache metadata
# typo check in menus

import argparse
import requests
import bs4 # sudo pacman -S --needed python-beautifulsoup4
import shlex
import subprocess
import os
import sys

URL_INDEX = r'https://nhentai.net/'
URL_PAGE = URL_INDEX + r'?page={page}'
URL_READ = URL_INDEX + r'g/{id}/{page}/'
URL_TAG = URL_INDEX + r'tag/{tag}/'

CACHE_DIR = os.path.expanduser(r'~/.cache/minq_nhentai/')
SETTINGS_DIR = os.path.expanduser(r'~/.config/minq_nhentai/')
HENTAIS_DIR = CACHE_DIR + r'hentai_sources/'

SOUP_PARSER = 'lxml'
NET_MAX_RETRIES = 20

THUMB_NAME = 'thumb'
DONE_POSTFIX = '.done'

class PageNotFoundException(Exception): pass

class Exception_page_not_found(Exception): pass
class Exception_page_unknown_error(Exception): pass

class Hentai:
    def __init__(s, id_, title, link, thumb, tags, languages, categories, pages, uploaded, parodies, characters, artists, groups):
        s.id_ = id_
        s.title = title
        s.link = link
        s.thumb_url = thumb
        s.tags = tags
        s.languages = languages
        s.categories = categories
        s.pages = pages
        s.uploaded = uploaded
        s.parodies = parodies
        s.characters = characters
        s.artists = artists
        s.groups = groups

    def __eq__(s, other):
        return s.id_ == other.id_

    def image_path(s, img):
        path = HENTAIS_DIR + str(s.id_) + '/' + img
        dir_ = os.path.dirname(path)
        if not os.path.isdir(dir_):
            os.makedirs(dir_)
        return path

    def image_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        return os.path.isfile(done)

    def image_set_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        with open(done, 'w'): pass

    def image_unset_cached(s, img):
        path = s.image_path(img)
        done = path + DONE_POSTFIX
        if os.path.isfile(done):
            os.remove(done)

    def image_cache(s, url, img):
        s.image_unset_cached(img)
        data = receive_raw(url)
        with open(s.image_path(img), 'wb') as f: f.write(data)
        s.image_set_cached(img)

    def image_print(s, img):
        assert s.image_cached(img)
        path = s.image_path(img)
        cmd = shlex.join(['viu', path])
        output = subprocess.run(cmd, shell=True, check=True, capture_output=False)

    def image_print_cache(s, url, img):
        if not s.image_cached(img):
            s.image_cache(url, img)
        s.image_print(img)

    def show(s):
        print(f'Title: {s.title}')
        print(f'Pages: {s.pages}')
        print(s.link)
        for t in s.tags: print(t)
        for a in s.artists: print(a)
        for l in s.languages: print(l)
        s.print_thumb()

    def print_thumb(s):
        if not s.image_cached(THUMB_NAME):
            s.image_cache(s.thumb_url, THUMB_NAME)
        s.image_print(THUMB_NAME)

    def contains_tag(s, tag):
        for t in s.tags:
            if tag == t.name:
                return True
        return False

    def reading_loop(s):
    
        page_num = 1

        while page_num <= s.pages and page_num >= 1:

            if not s.image_cached(str(page_num)):
                print('downloading...')

                url = URL_READ.format(id=s.id_, page=page_num)
                data = receive(url)

                soup = bs4.BeautifulSoup(data, SOUP_PARSER)
                link = soup.find(id='image-container').img['src']

                s.image_cache(link, str(page_num))

            print(f'Page: {page_num} / {s.pages}')
            s.image_print(str(page_num))

            # TODO download pages here
            c = input('>> ', 'q')

            if c in ['', 'n']:
                page_num += 1
            elif c == 'p':
                page_num -= 1
            elif c == 'q':
                break
            else:
                alert(f'Unknown command: {c}')

class Tag:
    prefix = 'Tag'
    def __init__(s, name, link, count):
        s.name = name
        s.link = link
        s.count = count
    def __repr__(s):
        return f'-> {s.prefix}: {s.name} ({s.count}) {s.link}'
class Language(Tag): prefix = 'Language'
class Category(Tag): prefix = 'Category'
class Parody(Tag): prefix = 'Parody'
class Character(Tag): prefix = 'Character'
class Artist(Tag): prefix = 'Artist'
class Group(Tag): prefix = 'Group'

_input = input
def input(msg, if_interrupted):
    try:
        return _input(msg)
    except KeyboardInterrupt:
        return if_interrupted

def alert(msg=''):
    print(msg)
    input('PRESS ENTER TO CONITNUE', -1)

def image_cache(url, id_, img_name):
    data = receive_raw(url)
    path = HENTAIS_DIR + str(id_) + '/' + img_name, 'w'
    with open(path) as f: f.write(data)
    with open(path + DONE_POSTFIX, 'w'): pass

def receive_raw(url):
    for _ in range(NET_MAX_RETRIES):
        page = requests.get(url)

        if page.ok:
            return page.content

        match (page.status_code, page.reason):
            case (404, 'Not Found'):
                raise Exception_page_not_found()
            case _:
                raise Exception_page_unknown_error(f'{url} {page.status_code} {page.reason}')
    assert False

def receive(url):
    return receive_raw(url).decode()

def does_tag_exist(tag):
    url = URL_TAG.format(tag=tag)
    try:
        receive(url)
    except Exception_page_not_found:
        return False
    return True

def scrape_hentais(url_page):
    page_num = 0
    while True:
        page_num += 1

        url = url_page.format(page=page_num)
        data = receive(url)

        soup = bs4.BeautifulSoup(data, SOUP_PARSER)

        container = soup.find(class_='container index-container')

        for hentai in container.find_all(class_='cover'):
            link = URL_INDEX + hentai['href']
            thumb_smol = hentai.find(class_='lazyload')['data-src']
            title = hentai.find(class_='caption').text

            id_ = link.split('/')[-2]
            id_ = int(id_)

            data = receive(link)
            soup = bs4.BeautifulSoup(data, SOUP_PARSER)

            thumb = soup.find(class_='lazyload')['data-src']

            def scrape_tag_container(container):

                meta = container.text.strip().replace('\n','').replace('\t','')

                tag_counts = container.find(class_='tags').find_all(class_='count')
                tags = [t.parent for t in tag_counts]
                assert len(tag_counts) == len(tags)
                tag_names = [t.find(class_='name').text for t in tags]
                tag_counts = [t.find(class_='count').text for t in tags]
                tag_links = [URL_INDEX + t['href'] for t in tags]

                assert len(tags) == len(tag_names) == len(tag_counts) == len(tag_links)
                return meta, tag_names, tag_links, tag_counts

            containers = soup.find_all(class_='tag-container field-name') + soup.find_all(class_='tag-container field-name hidden')

            tags = []
            languages = []
            categories = []
            parodies = []
            characters = []
            artists = []
            groups = []
            pages = None
            uploaded = None
            for container in containers:
                meta, n,l,c = scrape_tag_container(container)

                if meta.startswith('Pages:'):
                    pages = meta[len('Pages:'):]
                    pages = int(pages)
                elif meta.startswith('Uploaded:'): # TODO fix this
                    uploaded = meta[len('Uploaded:'):] + ' (this time is currently bugged)'
                else:

                    for n,l,c in zip(n,l,c):
                        if meta.startswith('Tags:'):
                            tags.append(Tag(n,l,c))
                        elif meta.startswith('Languages:'):
                            languages.append(Language(n,l,c))
                        elif meta.startswith('Categories:'):
                            categories.append(Category(n,l,c))
                        elif meta.startswith('Parodies:'):
                            parodies.append(Parody(n,l,c))
                        elif meta.startswith('Characters:'):
                            characters.append(Character(n,l,c))
                        elif meta.startswith('Artists:'):
                            artists.append(Artist(n,l,c))
                        elif meta.startswith('Groups:'):
                            groups.append(Group(n,l,c))
                        else:
                            assert False

            yield Hentai(id_, title, link, thumb, tags, languages, categories, pages, uploaded, parodies, characters, artists, groups)

def interactive_hentai_enjoyment(required_tags):

    CMDS = []
    CMDS.append(CMD_QUIT := ['quit', 'q', 'exit', 'e'])
    CMDS.append(CMD_NEXT := ['next hentai', 'next', 'n'])
    CMDS.append(CMD_PREV := ['previous hentai', 'previous', 'prev', 'p'])
    CMDS.append(CMD_READ := ['read hentai', 'read', 'enjoy', 'cum', 'wank', 'sex'])
    CMDS.append(CMD_TAG := ['filter by tags', 'tags', 'tag'])

    assert type(required_tags) in (list, tuple)

    for tag in required_tags:
        if not does_tag_exist(tag):
            print(f"Tag doesn't exist: {tag}")
            sys.exit(1)

    if len(required_tags) == 0:
        url_page = URL_INDEX
    else:
        url_page = URL_TAG.format(tag=required_tags[0])
        required_tags = required_tags[1:]

    running = True
    hentais = []
    ind = 0

    for hentai in scrape_hentais(url_page):

        find_new_hentai = False

        for h in hentais:
            if h == hentai:
                find_new_hentai = True
                break

        for tag in required_tags:
            if not hentai.contains_tag(tag):
                find_new_hentai = True
                break

        if find_new_hentai:
            continue

        hentais.append(hentai)

        while running:

            if ind >= len(hentais):
                break
            hentai = hentais[ind]

            hentai.show()

        
            c = input('> ', CMD_QUIT[0])

            if c == '':
                c = CMD_NEXT[0]

            if c in CMD_QUIT:
                running = False
            elif c in CMD_NEXT:
                ind += 1
            elif c in CMD_PREV:
                ind -= 1
            elif c in CMD_READ:
                hentai.reading_loop()
            elif c in CMD_TAG:
                tags = []
                doit = True
                while doit:
                    tag = input('Enter tag>> ', -1)
                    if tag == -1:
                        doit = False
                        continue
                    if tag == '':
                        break
                    if not does_tag_exist(tag):
                        alert(f"Tag doesn't exist: {tag}")
                        continue
                    tags.append(tag)
                else:
                    continue
                if len(tags) == 0:
                    alert('Warning: No tags specified')
                return interactive_hentai_enjoyment(tags)
            
            else:
                print(f'Unknown command: {c}')
                print('List of available commands:')
                for cmd in CMDS:
                    print(f'-> {cmd}')
                alert()

        else:
            break
            
def main():
    parser = argparse.ArgumentParser(description='Command line port of nhentai')
    parser.add_argument('--tags', nargs='+', help='Tags required for the hentai', default=[])
    args = parser.parse_args()

    tags = args.tags

    interactive_hentai_enjoyment(tags)

if __name__ == '__main__':
    main()
