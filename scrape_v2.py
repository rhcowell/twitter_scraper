from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from time import sleep, time
import json
import datetime
import csv
from queue import Queue
from threading import Thread
import Tweepy

# changes sleep time (in seconds)
delay = 1

with open('api_keys.json') as f:
    keys = json.load(f)

auth = tweepy.OAuthHandler(keys['consumer_key'], keys['consumer_secret'])
auth.set_access_token(keys['access_token'], keys['access_token_secret'])
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


def scrape_user(user, number_of_workers=4):
    print("Gathering user info on " + str(user))
    
    options = Options()
    options.set_headless(headless=True)
    driver = webdriver.Chrome(chrome_options=options)

    url = 'https://twitter.com/' + user
    driver.get(url)

    bio = get_bio(driver)
    join_date = get_join_date(driver)
    total_tweets = get_tweet_number(driver)
    following = get_following_number(driver)
    followers = get_followers_number(driver)
    likes = get_likes_number(driver)

    driver.quit()

    f = csv.writer(open(user + '_profile.csv', 'w'))
    f.writerow([user, bio, join_date, total_tweets, following, followers, likes])
    
    print("Finished writing " + str(user) + "_profile.csv\n")

    today = datetime.datetime.now()
    delta = today - join_date
    days_per_250_tweets = (delta.days + 1) / ((total_tweets / 250) + 1)
    days_per_worker = int(days_per_250_tweets)

    retreived_tweets = scrape_tweets_selenium(user, join_date, number_of_workers, days_per_worker)

    if (len(retreived_tweets) == total_tweets):
        print("-------- SUCCESS --------")
    else:
        print(len(retreived_tweets))
        print(total_tweets)


#parent
def scrape_tweets_selenium(user, join_date, number_of_workers=4, days_per_worker=30):
    end_date = datetime.datetime.now()
    
    worker_start = join_date
    worker_end = increment_day(worker_start, days_per_worker)
    procs = []
    tweet_ids = []
    queue_in = Queue()
    queue_out = Queue()

    while (worker_start < end_date):
        queue_in.put((worker_start, worker_end))
        worker_start = increment_day(worker_start, days_per_worker)
        worker_end = increment_day(worker_end, days_per_worker)

    if (number_of_workers > queue_in.qsize()):
        number_of_workers = queue_in.qsize()

    for i in range(number_of_workers):
        queue_in.put('Quit')
    
    for i in range(number_of_workers):
        t = Thread(target=scrape_helper, args=(i + 1, user, queue_in, queue_out))
        t.start()

    queue_in.join()

    results = []

    for i in range(queue_out.qsize()):
        t = queue_out.get_nowait()
        results += t

    return results

#child
def scrape_helper(worker_number, user, queue_in, queue_out):

    while True:
        print('Waiting')
        date_range = queue_in.get()
        print('Thru')

        if date_range == 'Quit':
            break

        results = []
        options = Options()
        options.set_headless(headless=True)
        driver = webdriver.Chrome(chrome_options=options)
        start_time = time()
        

        start_date = date_range[0]
        end_date = date_range[1]

        since = format_day(start_date)
        until = format_day(end_date)
        url = form_url(user, since, until)

        driver.get(url)
        sleep(delay)

        try:
            found_tweets = driver.find_elements_by_css_selector('li.js-stream-item')
            prev = len(found_tweets)
            stop = 0

            while True:
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
                found_tweets = driver.find_elements_by_css_selector('li.js-stream-item')
                
                if prev == len(found_tweets):
                    sleep(delay)
                    stop += 1
                elif prev < len(found_tweets):
                    stop = 0
                if stop >= 5:
                    break

                prev = len(found_tweets)
        
            for tweet in found_tweets:
                try:
                    id = tweet.find_element_by_css_selector('.time a.tweet-timestamp').get_attribute('href').split('/')[-1]
                    results.append(id)
                except StaleElementReferenceException as e:
                    print('lost element reference', tweet)

        except NoSuchElementException:
            print("Worker #" + str(worker_number) + ": NO TWEETS ERROR\n")
        except:
            driver.quit()
            print("Worker #" + str(worker_number) + ": ERROR\n")
            queue_in.put(date_range)
            queue_in.task_done()
            continue

        driver.quit()
        queue_out.put(results)

        print("Worker #" + str(worker_number) + ": " + str(len(results)) + " tweets from " + since + " to " + until + " in %s seconds\n" % int(time() - start_time))
        queue_in.task_done()

    queue_in.task_done()

def scrape_tweets_api(user, join_date):
    api.
    
def get_join_date(driver):
    join_date = driver.find_element_by_class_name('ProfileHeaderCard-joinDate').find_element_by_class_name('ProfileHeaderCard-joinDateText').get_attribute('title')
    return datetime.datetime.strptime(' '.join(join_date.split()[-3:]), '%d %b %Y')

def get_bio(driver):
    return driver.find_element_by_class_name('ProfileHeaderCard').find_element_by_tag_name('p').text

def get_tweet_number(driver):
    user_details = driver.find_element_by_class_name('ProfileNav').find_element_by_class_name('ProfileNav-list').find_elements_by_tag_name('li')
    return int(user_details[0].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count'))

def get_followers_number(driver):
    user_details = driver.find_element_by_class_name('ProfileNav').find_element_by_class_name('ProfileNav-list').find_elements_by_tag_name('li')
    return int(user_details[2].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count'))

def get_following_number(driver):
    user_details = driver.find_element_by_class_name('ProfileNav').find_element_by_class_name('ProfileNav-list').find_elements_by_tag_name('li')
    return int(user_details[1].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count'))

def get_likes_number(driver):
    user_details = driver.find_element_by_class_name('ProfileNav').find_element_by_class_name('ProfileNav-list').find_elements_by_tag_name('li')
    return int(user_details[3].find_element_by_tag_name('a').find_element_by_class_name('ProfileNav-value').get_attribute('data-count'))

def format_day(date):
    day = '0' + str(date.day) if len(str(date.day)) == 1 else str(date.day)
    month = '0' + str(date.month) if len(str(date.month)) == 1 else str(date.month)
    year = str(date.year)
    return '-'.join([year, month, day])

def form_url(user, since, until):
    p1 = 'https://twitter.com/search?f=tweets&vertical=default&q=from%3A'
    p2 =  user.lower() + '%20since%3A' + since + '%20until%3A' + until + 'include%3Aretweets&src=typd'
    return p1 + p2

def increment_day(date, i):
    return date + datetime.timedelta(days=i)

if __name__ == "__main__":
    scrape_user('DelaneyBry87', number_of_workers=10)


