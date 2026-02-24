import re                       #피드를 나누기 위한 정규표현식 라이브러리
from datetime import datetime   #시간 처리 라이브러리
import html                     #타이틀 행 특수문자 깨지는 거 처리용 라이브러리
import os                       #현재 파일 위치 확인용 라이브러리

import feedparser               # RSS 받아오는 라이브러리
from mastodon import Mastodon   # 포스트 발송용 라이브러리

import logging                  # 로그 출력용 라이브러리
import logging.handlers

DEFAULT_DIR = os.path.dirname(os.path.realpath(__file__))

def main():

    logger.info("Service Start")
    # TODO 명령줄 인수를 받아서 RSS 입력(신규 URL), 출력 방향(마스토돈/기타 SNS 등) 설정
    # TODO RSS를 안 읽고 마스토돈 멘션으로 넘어온 명령만 처리하는 것도 구현하고 싶음(이건 프로젝트 분리하는 게 나을지도)

    try:
        feed_list = []          #파일에서 RSS 주소랑 관련정보 불러다 리스트로 저장하는 데 씀, 자료형은 <feedlist>
        feed_latest_dic = {}    #이전 갱신시각 확인하는 데 씀, {index : [RSS, latest]}형태로 저장
        new_flag = False        #새로운 피드가 추가되었는지 여부, late.st 파일을 갱신할 필요가 있는지 판단하는 데 씀

        feed_list = read_rss_watchlist(DEFAULT_DIR + '/feeder.ini')
        feed_latest_dic, new_flag = read_latest_date(DEFAULT_DIR + '/late.st')

        mastodon = mastodon_login(DEFAULT_DIR + '/tweetkey.ini')

        for feed in feed_list:
            try:
                # late.st에 내용이 없거나 RSS 주소가 바뀐 경우에는 feed_latest_dic만 갱신
                if not feed_latest_dic[feed.index][0] == feed.RSS:
                    raise KeyError
                
                # TODO new_post에 포스트할 게시물을 저장하고 RSS 입력단 / 포스트 출력단 분리
                # TODO 이렇게 구성하면 입력단으로 RSS 말고 다른 걸 받았을 때 확장성이 좋음(유튜브/비리비리)
                new_post, feed_latest_dic[feed.index] = rss2compare(feed, feed_latest_dic[feed.index], mastodon)
                new_flag = new_flag or new_post

            except KeyError:
                try:            # RSS 불러오기
                    parsingdata = feedparser.parse(feed.RSS)
                except:
                    logger.critical("Error in feedparser.parse, name = " + feed.name)
                    raise

                # 가장 최근 게시글 검색
                latest_time = datetime.strptime('15 Oct 1991 17:50:15 +0900', "%d %b %Y %X %z")
                for entry in parsingdata.entries:
                    latest_time = max(latest_time, datetime.strptime(entry.published, "%a, %d %b %Y %X %z"))
                
                feed_latest=[feed.RSS, latest_time]
                logger.info("check latest feed in " + feed.name + ", " + latest_time.strftime("%a, %d %b %Y %X %z"))
                feed_latest_dic[feed.index] = feed_latest

                new_flag = True

        if new_flag:
            # late.st 파일 갱신 필요
            write_latest_date(DEFAULT_DIR + '/late.st', feed_latest_dic)

    except Exception as exerr:
        logger.critical('Critical Error : ' + str(exerr.args[0]))
        raise

    finally:
        logger.info("Service End")

def mastodon_login(filename: str=DEFAULT_DIR + "/tweetkey.ini") -> Mastodon:
    """
    filename 인수로 들어온 파일에서 읽은 키로 마스토돈에 로그인합니다.
    
    Args:
        filename (str): 인수(access_token='토큰', api_base_url='로그인하려는 인스턴스 주소')
    
    Returns:
        Mastodon: 로그인된 세션
    """

    with open(filename, "r", encoding="utf-8-sig") as pathkey:
        text = pathkey.read()
    
        at = re.compile('(?<=access_token=").*?(?=")').search(text).group(0)
        apu = re.compile('(?<=api_base_url=").*?(?=")').search(text).group(0)
    
    logger.info("Mastodon Login Success")

    return Mastodon(access_token=at, api_base_url=apu)

def read_rss_watchlist(filename: str=DEFAULT_DIR + "/feeder.ini") -> list:
    """
    filename 인수로 들어온 파일을 리스트에 입력합니다. 해당 파일은 감시 대상 RSS의 목록입니다.
    
    Args:
        filename (str): 감시 대상 RSS의 목록,
            구조: {index="150" prefix="デッドボールP" name="デッドボールP" RSS="http://www.nicovideo.jp/mylist/3390381?rss=2.0"}
    
    Returns:
        list: 감시 대상 RSS의 목록
    """
    # TODO pickle 이용해서 저장방식 개선

    logger.info("Reading feeder.ini...")
    feed_list=[]         #<feedlist>를 모아놓은 리스트

    with open(filename, "r", encoding="utf-8-sig") as read_rss_watchlist:
        
        lines = read_rss_watchlist.readlines()   # <lines>에 파일 전체 입력

        for line in lines:          # <line>으로 행별로 쪼갬
            if not line[0] == "#":      # 주석행은 무시
                try:                    # 숫자로 된 index=""이 있는가 확인
                    indextext=int(re.compile('(?<=index=").*?(?=")').search(line).group(0))
                except AttributeError:  # 없는 행은 무시해줌
                    pass
                except:                 # 다른 에러는 처리
                    logger.error("Error in feeder.ini : " + line)
                    raise
                else:                   # <index>가 중복이면 에러 표출
                    if indextext in [f.index for f in feed_list]:
                        logger.error("Duplicate index found in feeder.ini : " + str(indextext))
                        raise CustomError("<index> 필드에 " + str(indextext) + "가 둘 이상입니다")
                    
                    feed_list.append(RSSFeedList(indextext, line))
                    
    logger.info("Reading feeder.ini Success")
    return feed_list

def read_latest_date(filename: str=DEFAULT_DIR + "/late.st") -> (dict, bool):
    """
    filename 인수로 들어온 파일을 딕셔너리에 입력합니다. 해당 파일은 이전 갱신 시각을 저장하는 파일입니다.
    
    Args:
        filename (str): 감시 대상 RSS의 이전 갱신 시각이 저장된 파일,
            구조: {index="40" RSS="http://www.nicovideo.jp/mylist/5113852?rss=2.0" latest="Sat, 09 Apr 2016 19:00:35 +0900"}
    
    Returns:
        tuple: (feed_latest, new_flag)
            feed_latest: 감시 대상 RSS의 이전 갱신 시각 딕셔너리
                구조: {index : [RSS, latest]}
            new_flag: 새로운 피드가 추가되었는지 여부 (bool)
    """
    logger.info("Reading late.st...")
    feed_latest={}
    
    try:
        dic = open(filename, "r", encoding="utf-8-sig")
    except FileNotFoundError:
        logger.warning("Writing late.st...")
        pass
    else:
        lines = dic.readlines()
        for line in lines:
            try:
                dic_index = int(re.compile('(?<=index=").*?(?=")').search(line).group(0))
                dic_RSS = re.compile('(?<=RSS=").*?(?=")').search(line).group(0)
                dic_latest = re.compile('(?<=latest=").*?(?=")').search(line).group(0)
            except AttributeError:  #깨져서 제대로 나오지 않는 행이 있다면 그 행은 무시함
                pass
            else:
                feed_latest[int(dic_index)] = [dic_RSS, datetime.strptime(dic_latest, "%a, %d %b %Y %X %z")]
        dic.close()
    
    logger.info("Reading late.st Success")

    return feed_latest, False

def write_latest_date(filename=DEFAULT_DIR + "/late.st", feed_latest={}):
    """
    filename 인수로 들어온 파일에 feed_latest 인수로 들어온 딕셔너리의 내용을 작성합니다. 해당 파일은 이전 갱신 시각을 저장하는 파일입니다.

    Args:
        filename (str): 감시 대상 RSS의 이전 갱신 시각이 저장된 파일,
            구조: {index="40" RSS="http://www.nicovideo.jp/mylist/5113852?rss=2.0" latest="Sat, 09 Apr 2016 19:00:35 +0900"}
        feed_latest (dict): 감시 대상 RSS의 이전 갱신 시각 딕셔너리
            구조: {index : [RSS, latest]}
        new_flag (bool): 새로운 피드가 추가되었는지 여부
    """
    logger.info("Writing late.st...")
    with open(filename, "w", encoding="utf-8-sig") as dic:
        for feed in feed_latest:
            try:
                dic.write('index="' + str(feed) + '" ')
                dic.write('RSS="' + feed_latest[feed][0] + '" ')
                dic.write('latest="' + feed_latest[feed][1].strftime("%a, %d %b %Y %X %z") + '"\n')
            except:     #에러가 있어 제대로 출력되지 않는 행이 있다면 그 행은 건너뛰고 다음 행부터 작성
                dic.write('\n')
                logger.warning("late.st output error in index = " + str(feed))
                pass
    logger.info("Writing late.st Success")

def rss2compare(rss_feed, feed_latest, api):
    """
    rss_feed 인수로 들어온 RSS 피드의 내용을 feed_latest 인수로 들어온 딕셔너리의 갱신 시각과 비교하여,
    새로운 게시물이 있는 경우 api 인수로 들어온 Mastodon 세션을 이용해 트윗을 발송합니다.
    또한, 새로운 게시물이 있는 경우 feed_latest 딕셔너리를 갱신합니다.

    Args:
        rss_feed: RSS 피드의 정보가 담긴 객체 (구조는 <RSSFeedList>)
        feed_latest: 감시 대상 RSS의 이전 갱신 시각이 저장된 딕셔너리 (구조는 {index : [RSS, latest]})
        api: Mastodon 세션
    
    Returns:
        bool: 새로운 게시물이 있는지 여부
        datetime: 가장 최근 게시물의 등록 시각
    """

    new_flag = False

    # TODO 캐싱해서 데이터 수집량 줄이기

    try:            # 우선 RSS 불러오기
        parsingdata = feedparser.parse(rss_feed.RSS)
    except:         # 실제로 에러를 내보고 판단하자(우선 RSS주소 미스 정도로는 에러 안 남)
        logger.critical("Error in feedparser.parse, name = " + rss_feed.name)
        raise

    dic_latest = feed_latest[1]

    # 갱신시각과 비교해서 피드에 갱신시각보다 최신자료가 있으면 트위터에 업로드
    # TODO 예약 발송의 경우 실제로 업로드되면 발송되도록 하고 싶음

    latest_time = dic_latest        # 기존의 최근 업로드 시각 입력
    parsingdata.entries.reverse()   # 엔트리 순서 뒤집기(등록순으로 정렬시에 과거 자료부터 트위터에 올라가게끔)

    for entry in parsingdata.entries:
        entry_published = datetime.strptime(entry.published, "%a, %d %b %Y %X %z")
        if dic_latest < entry_published:
            new_flag = True         #late.st 파일을 갱신할 필요가 생김
            latest_time = max(latest_time, entry_published)
            
            #트위터로 entry.title이랑 entry.link 내보내기
            logger.info("update feed : " + entry.title)
            
            Write_Post(api, rss_feed, entry)
    feed_latest[1] = latest_time

    return new_flag, feed_latest

def Write_Post(api, rss_feed, entry):
    """
    api 인수로 들어온 Mastodon 세션을 이용해 포스트를 발송합니다.
    발송되는 포스트의 내용은 rss_feed 인수로 들어온 RSS 피드의 접두사, 접미사와 entry 인수로 들어온 게시물 내용입니다.

    Args:
        api: Mastodon 세션
        rss_feed: RSS 피드의 정보가 담긴 객체 (구조는 <feedlist>)
        entry: 게시물의 정보가 담긴 객체 (구조는 feedparser.parse()로 불러온 엔트리 객체)
    """
    
    if re.compile(rss_feed.filter).match(entry.title):          # 정규표현식 기반 필터
        entry.title = html.unescape(entry.title)                # 특수문자가 포함된 경우 깨져나오는 것 방지
        msg = rss_feed.prefix + entry.title + rss_feed.suffix
        msg = msg + "\n " + entry.link
        api.status_post(msg)

class CustomError(Exception):       #사용자 정의 오류
    def __init__(self, msg):        #<feedlist.index>값이 유일하지 않을 때 에러를 출력
        self.msg = msg              #피드에 RSS가 없을 때 에러를 출력

    def __str__(self):
        return self.msg

class RSSFeedList:
    """
    RSS 피드의 정보를 담는 클래스입니다. feeder.ini 파일에서 읽은 정보를 바탕으로 객체가 생성됩니다.

    Attributes:
        index (int): RSS 피드의 고유한 인덱스입니다. feeder.ini 파일의 index="" 필드에서 읽어옵니다.
        name (str): RSS 피드의 식별명입니다. feeder.ini 파일의 name="" 필드에서 읽어옵니다.
        prefix (str): RSS 피드의 접두어입니다. feeder.ini 파일의 prefix="" 필드에서 읽어옵니다. 기본값은 빈 문자열입니다.
        suffix (str): RSS 피드의 접미어입니다. feeder.ini 파일의 suffix="" 필드에서 읽어옵니다. 기본값은 빈 문자열입니다.
        RSS (str): RSS 피드의 주소입니다. feeder.ini 파일의 RSS="" 필드에서 읽어옵니다. 이 필드는 필수입니다.
        filter (str): RSS 피드의 제목에 적용할 정규표현식 필터입니다. feeder.ini 파일의 filter="" 필드에서 읽어옵니다.
                      기본값은 ".*"로, 모든 제목이 필터를 통과합니다.
    """

    index = ""      #Unique한 값
    name = ""       #식별명
    prefix = ""     #접두어
    suffix = ""     #접미어
    RSS = ""        #RSS 주소
    filter = ".*"   #출력을 위한 필터(기본값은 필터 안함)

    def __init__(self, index: int, rss_line: str):
        self.index = index
        self.addRSS(rss_line)

    def addRSS(self, text):     #class쪽에 빼놓는게 유지보수하기 편할 거 같아서 이 쪽으로 뺌
        try:                    #실사용은 <inputfile> 함수에서 함
            self.name = re.compile('(?<=name=").*?(?=")').search(text).group(0)
        except AttributeError:
            pass
        try:
            self.prefix = re.compile('(?<=prefix=").*?(?=")').search(text).group(0).encode('utf-8').decode('unicode_escape')
        except AttributeError:
            pass
        try:
            self.suffix = re.compile('(?<=suffix=").*?(?=")').search(text).group(0).encode('utf-8').decode('unicode_escape')
        except AttributeError:
            pass
        try:
            self.RSS = re.compile('(?<=RSS=").*?(?=")').search(text).group(0)
        except AttributeError:
            raise CustomError(str(self.index) + " : RSS가 없는 피드가 있습니다")
        try:
            self.filter = re.compile('(?<=filter=").*?(?=")').search(text).group(0)
        except AttributeError:
            pass

if __name__ == "__main__": 

  #로그 선언
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    #로그파일 만들 핸들러 선언
    eventHandler = logging.handlers.RotatingFileHandler(DEFAULT_DIR + '/event.log', maxBytes = 1024 * 1024, backupCount = 5)
        #1MByte, 5개까지 로그를 저장함
    eventHandler.setLevel(logging.INFO)
    eventHandler.setFormatter(logging.Formatter('%(asctime)s|%(levelname)s > %(message)s'))

    logger.addHandler(eventHandler) #핸들러 로거에 추가
    main()
