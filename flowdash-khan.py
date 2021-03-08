import json
import time
import os
import os.path
from glob import glob
import shutil
import sqlite3

import requests
from requests.auth import HTTPBasicAuth

from dotenv import load_dotenv
load_dotenv()

auth = HTTPBasicAuth(os.environ['FLOWDASH_USER'], os.environ['FLOWDASH_API_PASS'])

def get_cookies(where="HOST='www.khanacademy.org'") -> list:
    "Get firefox cookies"

    firefox_profile_path = glob(os.path.join(os.environ['HOME'], '.mozilla/firefox/*.default-release'))[0]

    src = os.path.join(firefox_profile_path, 'cookies.sqlite')
    dst = '/tmp/cookies.sqlite'

    # stupid hack since database is locked when in use, and I can't
    # figure out how to bypass it, or read the DB into memory
    shutil.copyfile(src, dst)

    with sqlite3.connect(dst) as conn:
        cursor = conn.execute(f'SELECT * FROM moz_cookies WHERE {where}')
        cookies_data = cursor.fetchall()
        keys = [d[0] for d in cursor.description]

        # TODO: Explicitly do this, some names arent the same
        # (host in sql vs domain in selenium), but it should be fine as long as
        # value and name are the same.
        cookies = [dict(zip(keys, cookie)) for cookie in cookies_data]

    # remove the temp database
    os.remove(dst)

    return cookies


def get_masterypoints(headless: bool = True) -> int:
    "Get the mastery points from khan academy using selenium"

    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException

    url = 'https://www.khanacademy.org/math/multivariable-calculus'
    selector = '[data-test-id="subject-points-earned-label"]'

    print('Launching webdriver')
    options = webdriver.FirefoxOptions()
    options.headless = headless
    driver = webdriver.Firefox(options=options)

    print('Adding cookies')

    # This is cursed https://stackoverflow.com/a/28331099
    driver.get('https://www.khanacademy.org/robots.txt')
    cookies = get_cookies()
    for cookie in cookies:
        driver.add_cookie(cookie)

    print('Navigating to ' + url)
    driver.get(url)

    print('Waiting for mastery points to appear')
    mastery_points_text = ''
    while mastery_points_text.strip() == '':
        try:
            elem = driver.find_element_by_css_selector(selector)
            mastery_points_text = elem.text
        except NoSuchElementException:
            # must not have loaded yet
            pass
        time.sleep(0.1)

    driver.close()

    mastery_points = mastery_points_text.split(' ')[0]
    return int(mastery_points)


def track_masterypoints(mastery_points: int):
    "Send the mastery points to flowdash"

    url = 'https://flowdash.co/api/tracking'

    print(f'Sending {mastery_points} to flowdash')
    resp = requests.post(url, auth=auth, data={
        "date": time.strftime('%Y-%m-%d'),
        "data": json.dumps({
            "masterypoints": mastery_points,
        }),
    })

    print(resp)
    print(resp.text)


def main():
    "Log mastery points to flowdash"
    mastery_points = get_masterypoints()
    print(mastery_points)
    track_masterypoints(mastery_points)

if __name__ == '__main__':
    main()
