from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep, time
import json
import datetime
import csv


# edit these three variables
user = 'realdonaldtrump'

end = datetime.datetime.now() # year, month, day
# only edit these if you're having problems
delay = 1  # time to wait on each page load before reading the page
driver = webdriver.Firefox()  # options are Chrome() Firefox() Safari()


url = 'https://twitter.com/' + user
driver.get(url)

profile = driver.find_element_by_class_name('ProfileHeaderCard')
bio = profile.find_element_by_tag_name('p').text
join = driver.find_element_by_class_name('ProfileHeaderCard-joinDate')
join_date = join.find_element_by_class_name('ProfileHeaderCard-joinDateText').get_attribute('title')
start = datetime.datetime.strptime(' '.join(join_date.split()[-3:]), '%d %b %Y')


details = driver.find_element_by_class_name('ProfileNav').find_element_by_class_name('ProfileNav-list')
user_details = details.find_elements_by_tag_name('li')


total_tweets = user_details[0].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count')
following = user_details[1].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count')
followers = user_details[2].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count')
likes = user_details[3].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count')



f = csv.writer(open(user + '_profile.csv', 'w'))
f.writerow([user, bio, start, total_tweets, following, followers, likes])

start = datetime.datetime.strptime('18 Apr 2017', '%d %b %Y')
# don't mess with this stuff
twitter_ids_filename = 'all_ids.json'
days = (end - start).days + 1
id_selector = '.time a.tweet-timestamp'
tweet_selector = 'li.js-stream-item'
user = user.lower()
ids = []

def format_day(date):
    day = '0' + str(date.day) if len(str(date.day)) == 1 else str(date.day)
    month = '0' + str(date.month) if len(str(date.month)) == 1 else str(date.month)
    year = str(date.year)
    return '-'.join([year, month, day])

def form_url(since, until):
    p1 = 'https://twitter.com/search?f=tweets&vertical=default&q=from%3A'
    p2 =  user + '%20since%3A' + since + '%20until%3A' + until + 'include%3Aretweets&src=typd'
    return p1 + p2

def increment_day(date, i):
    return date + datetime.timedelta(days=i)


start_time = time()

while start <= end:
    d1 = format_day(increment_day(start, 0))
    d2 = format_day(increment_day(start, 120))
    url = form_url(d1, d2)
    print(url)
    print(d1)
    driver.get(url)
    sleep(delay)

    try:
        found_tweets = driver.find_elements_by_css_selector(tweet_selector)
        prev = len(found_tweets)
        stop = 0

        while True:
            print('scrolling down to load more tweets')
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            found_tweets = driver.find_elements_by_css_selector(tweet_selector)
            
            if prev == len(found_tweets):
                sleep(delay)
                stop += 1
            elif prev < len(found_tweets):
                stop = 0
            if stop >= 5:
                break;

            prev = len(found_tweets)
    

        print('{} tweets found, {} total'.format(len(found_tweets), len(ids)))

        for tweet in found_tweets:
            try:
                id = tweet.find_element_by_css_selector(id_selector).get_attribute('href').split('/')[-1]
                ids.append(id)
            except StaleElementReferenceException as e:
                print('lost element reference', tweet)

    except NoSuchElementException:
        print('no tweets on this day')

    start = increment_day(start, 120)

print("--- %s seconds ---" % (time() - start_time))

try:
    with open(twitter_ids_filename) as f:
        all_ids = ids + json.load(f)
        data_to_write = list(set(all_ids))
        print('tweets found on this scrape: ', len(ids))
        print('total tweet count: ', len(data_to_write))
except FileNotFoundError:
    with open(twitter_ids_filename, 'w') as f:
        all_ids = ids
        data_to_write = list(set(all_ids))
        print('tweets found on this scrape: ', len(ids))
        print('total tweet count: ', len(data_to_write))

with open(twitter_ids_filename, 'w') as outfile:
    json.dump(data_to_write, outfile)

print('all done here')

driver.close()
