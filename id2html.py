#!/usr/bin/env python3
import re
from bs4 import BeautifulSoup
from collections import namedtuple
from itertools import groupby
from operator import itemgetter

first_article_id = 9
destination = 'blah-clean/blah_{0}.html'

article = namedtuple('Article', ['section_title', 'article_title',
                                 'article_author', 'footnotes', 'author_bio', 'text'])

with open('blah-raw/blah.html', 'rb') as f:
    soup = BeautifulSoup(f.read(), 'lxml')

body = soup.find('body')
stories = body.find_all('div', id=re.compile('_idContainer.*'))
all_articles = []

for story in stories:
    article_id = int(story.attrs['id'][-3:])
    if ('class' in story.attrs and 'Basic-Text-Frame' in story.attrs['class'] and
            article_id >= first_article_id):
        # Italic to <i>
        italics_raw = story.find_all('span', class_=re.compile('_Italic'))
        for tag in italics_raw:
            tag.name = 'i'
            del tag['class']
            del tag['id']

        # Bold to <b>
        bold_raw = story.find_all('span', class_=re.compile('_Bold'))
        author_bio = story.find_all('span', class_=re.compile('Author-name-in-bio'))
        for tag in bold_raw + author_bio:
            tag.name = 'b'
            del tag['class']
            del tag['id']

        # Small caps to .small
        small_raw = story.find_all('span', class_=re.compile('Small-caps'))
        start_caps_raw = story.find_all('span', class_=re.compile('Chapter-start-caps'))
        for tag in small_raw + start_caps_raw:
            tag.name = 'span'
            del tag['class']
            del tag['id']
            tag['class'] = 'small-caps'

        # <h1> and <h2>
        h1s_raw = story.find_all('p', class_=re.compile('Heading-1'))
        for tag in h1s_raw:
            tag.name = 'h4'
            del tag['class']
            del tag['id']

        h2s_raw = story.find_all('p', class_=re.compile('Heading-2'))
        for tag in h2s_raw:
            tag.name = 'h5'
            del tag['class']
            del tag['id']

        # Look for table containing section title and extract it
        tables_raw = story.find_all('table')
        section_title = None
        for table in tables_raw:
            section_title_raw = table.find('p', class_=re.compile('Section-title'))
            if section_title_raw:
                section_title = ''.join([str(chunk) for chunk in section_title_raw.contents])
                table.extract()

        # Find and extract article title
        article_title_raw = story.find('p', class_=re.compile('Chapter-title'))
        if article_title_raw:
            article_title = article_title_raw.get_text()
            article_title_raw.extract()
        else:
            article_title = None

        # Find and extract article author
        article_author_raw = story.find('p', class_=re.compile('_Author'))
        if article_author_raw:
            article_author = article_author_raw.get_text()
            article_author_raw.extract()
        else:
            article_author = None

        # Find and extract author bio
        bio_raw = story.find('p', class_=re.compile('Author-bio'))
        if bio_raw:
            author_bio = ''.join([str(chunk) for chunk in bio_raw.contents])
            bio_raw.extract()
        else:
            author_bio = None

        # Find, clean, and extract footnotes
        footnotes_raw = story.find('div', class_='_idFootnotes')
        footnotes_clean = []
        if footnotes_raw:
            footnotes = footnotes_raw
            footnotes_raw.extract()

            notes_raw = footnotes.find_all('div', class_=re.compile('_idFootnote'))
            for note in notes_raw:
                # Get the note number and clean up extra reference cruft
                note_number_raw = note.find('a', class_=re.compile('idFootnoteAnchor'))
                note_number = note_number_raw.get_text()
                back_fn_link = soup.new_tag('a', href='#_ednref{0}'.format(note_number))
                back_fn_link['name'] = '_edn{0}'.format(note_number)
                back_fn_link.string = note_number + '.'
                note_number_raw.replace_with(back_fn_link)

                del note['class']
                del note['id']
                note['id'] = 'fn' + note_number

                # Clean footnote <p> attributes
                note_ps = note.find_all('p', class_=re.compile('Footnote'))
                for note_p in note_ps:
                    del note_p['class']
                    del note_p['id']
                    footnotes_clean.append(str(note_p))
                # footnotes_clean.append(str(note_ps))
            # print(footnotes.contents)
            # print('\n'.join(footnotes_clean))
        else:
            footnotes = None

        # Get rid of <hr>s
        [hr.extract() for hr in story.find_all('hr')]

        # Clean unindented paragraphs
        unindented_raw = story.find_all('p', class_=re.compile('Normal--no-indent'))
        for tag in unindented_raw:
            tag.name = 'p'
            del tag['class']
            del tag['id']
            tag['class'] = 'no-indent'

        # TODO: Clean all other <p>s

        # There's no(?) easy way to wrap multiple tags in BeautifulSoup, so
        # this is kind of convoluted, but it works. First save all paragraph
        # indexes for quotes into a list (quote_ps):
        # Example: [9, 11, 17, 18, 19, 20, 21, 22, 25, 26, 27, 28, 29, 30]
        #
        # Then create a list of lists of consecutive numbers:
        # Example: [[9], [11], [17, 18, 19, 20, 21, 22], [25, 26, 27, 28, 29, 30]]
        #
        # Loop through that list of lists. If there's just one paragraph, wrap
        # it in a <blockquote> using .wrap(). If there's more than one
        # paragraph, create a new <blockquote>, append each paragraph to it as
        # children, and extract those paragraphs
        # quote_ps = []
        # for i, tag in enumerate(story):
        #     if not isinstance(tag, NavigableString):
        #         if '_Quote' in tag['class'][0]:
        #             quote_ps.append(i)
        #             del tag['class']
        #             del tag['id']
        all_ps = story.find_all('p')
        quote_ps = []
        for i, tag in enumerate(all_ps):
            if '_Quote' in tag['class'][0]:
                quote_ps.append(i)
                del tag['class']
                del tag['id']

        # Find runs of consecutive numbers (from example in docs):
        #   https://docs.python.org/3.0/library/itertools.html#examples
        quotes_consec = []
        for k, g in groupby(enumerate(quote_ps), lambda t: t[0] - t[1]):
            quotes_consec.append(list(map(itemgetter(1), g)))
        # TODO: When using story instead of all_ps, paragraphs are no longer consecuitve (because they have whitespace between them)

        for quote in quotes_consec:
            # Use regular .wrap() function if there's just one
            if len(quote) == 1:
                all_ps[quote[0]].wrap(soup.new_tag("blockquote"))
            # No easy way to wrap multiple elements, so create a new tag,
            # append elements to it, and extract them
            # TODO: Fix this. It's stripping all these <p>s out for some reason
            # else:
            #     blockquote = soup.new_tag('blockquote')
            #     for q in quote:
            #         blockquote.append(all_ps[q])
            #         # all_ps[q].extract()

            #     # Insert the newly populated blockquote into the all_ps tree
            #     all_ps.insert(quote[0], blockquote)
        # print(all_ps)

        # Renumber footnotes more sensibly
        note_ref_template = '<a href="#_edn{0}" name="_ednref{0}"><sup>{0}</sup></a>'
        note_template = ''
        all_notes = []

        superscript_raw = story.find_all('span', class_=re.compile('Superscript'))
        for sup in superscript_raw:
            if '_idFootnoteLink' in str(sup):
                note_number = sup.get_text()
                all_notes.append(int(note_number))
                sup.replace_with(BeautifulSoup(note_ref_template.format(note_number), 'html.parser'))

        clean_story = ('\n'.join([str(chunk) for chunk in story.contents if chunk != '\n'])
                         .replace('Main-text_Normal--tighter--no-indent', 'no-indent')
                         .replace(' class="Main-text_Normal"', '')
                         .replace(' class="Main-text_Normal--tighter-"', ''))
        clean_article = article(section_title, article_title, article_author,
                                '\n'.join(footnotes_clean).replace('\t', '').replace('.</a>.', '.</a>'),
                                author_bio, ''.join(clean_story))
        all_articles.append(clean_article)

article_format = """<h2>{0.article_title}</h2>
<h4><i>{0.article_author}</i></h4>

{0.text}

<blockquote>{0.author_bio}</blockquote>

<hr>
<p>NOTES</p>
{0.footnotes}
"""

for n, clean_article in enumerate(all_articles):
    if clean_article.section_title:
        section_title = "<h1>{0.section_title}</h1>\n".format(clean_article)
    else:
        section_title = ""

    final_article = article_format.format(clean_article)

    with open(destination.format(n + 1), 'w') as f:
        f.write(section_title + final_article)

# TODO: Remove <br>s from links
# TODO: Add actual <a> tags to links
