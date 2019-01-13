#!/usr/bin/python
# -*- coding: utf-8 -*-
    
import re                       #피드를 나누기 위한 정규표현식 라이브러리
from datetime import datetime   #시간 처리 라이브러리
import html                     #타이틀 행 특수문자 깨지는 거 처리용 라이브러리
import os                       #현재 파일 위치 확인용 라이브러리

import feedparser               #RSS 받아오는 라이브러리
import twitter                  #트윗 발송용 라이브러리

import logging                  #로그 출력용 라이브러리
import logging.handlers

DEFAULT_DIR = os.path.dirname(os.path.realpath(__file__))
######################################class 선언부######################################

class feedlist:
    index = ""      #Unique한 값
    name = ""       #식별명
    prefix = ""     #접두어
    suffix = ""     #접미어
    RSS = ""        #RSS 주소
    filter = ".*"   #출력을 위한 필터(기본값은 필터 안함)

    def addRSS(self, text):     #class쪽에 빼놓는게 유지보수하기 편할 거 같아서 이 쪽으로 뺌
        try:                    #실사용은 <inputfile> 함수에서 함
            self.name = re.compile('(?<=name=").*?(?=")').search(text).group(0)
        except AttributeError:
            pass
        try:
            self.prefix = re.compile('(?<=prefix=").*?(?=")').search(text).group(0)
        except AttributeError:
            pass
        try:
            self.suffix = re.compile('(?<=suffix=").*?(?=")').search(text).group(0)
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

######################################에러 선언부######################################

class CustomError(Exception):       #사용자 정의 오류
    def __init__(self, msg):        #<feedlist.index>값이 유일하지 않을 때 에러를 출력
        self.msg = msg              #피드에 RSS가 없을 때 에러를 출력

    def __str__(self):
        return self.msg

######################################함수 선언부######################################

def inputfile(filename=DEFAULT_DIR + "/feeder.ini"):

#<filename>에서 파일을 입력받아서 RSS주소랑 기타등등(<feedlist>에서 정의한 거) 정리해서 변수 형태로 출력해주는 함수
#파일 구조 : {index="150" prefix="デッドボールP" name="デッドボールP" RSS="http://www.nicovideo.jp/mylist/3390381?rss=2.0"}

    feed_list=[]         #<feedlist>를 모아놓은 리스트

    with open(filename, "r", encoding="utf-8-sig") as inputfile:
        
        lines = inputfile.readlines()   #<lines>에 파일 전체 입력

        for line in lines:          #<line>으로 행별로 쪼갬
            if not line[0] == "#":      #주석행은 무시
                try:                    #숫자로 된 index=""이 있는가 확인
                    indextext=int(re.compile('(?<=index=").*?(?=")').search(line).group(0))
                except AttributeError:  #없는 행은 무시해줌
                    pass
                except:                 #다른 에러는 처리
                    raise
                else:                   #<index>이 있으면 중복인지 확인
                    for i in range(0,len(feed_list)):
                        if feed_list[i].index == indextext:    #유감이네요! 중복입니다! 에러머겅!
                            raise CustomError("<index> 필드에 " + indextext + "가 둘 이상입니다")
                    #print(len(feed_list))
                    feed_list.append(feedlist())
                    feed_list[len(feed_list) - 1].index = indextext     #<index> 입력
                    feed_list[len(feed_list) - 1].addRSS(line)
                    
                    
    #print(len(feed_list))    #에러 없이 여기까지 오면 출력됨(디버그용)
    return feed_list


###

def inputdic(filename=DEFAULT_DIR + "/late.st"):

#파일 구조 : {index="40" RSS="http://www.nicovideo.jp/mylist/5113852?rss=2.0" latest="Sat, 09 Apr 2016 19:00:35 +0900"}
#<feed_latest>에 {index : [RSS, latest]} 형태로 내보냄

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

    return feed_latest, False


def outputdic(filename=DEFAULT_DIR + "/late.st", feed_latest={}, new_flag=False):
    if new_flag:
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


###

def rss2compare(feed_lst, api):

#갱신시각 파일과 비교해서 피드 내용물이 최신인지 아닌지 검증하는 함수
#갱신이 있다면 트윗을 보내고 갱신시각 파일 갱신 준비
#갱신시각 파일이 없는 경우 작성을 위해 게시글 발행 시각을 조사

    new_flag = False

    try:            #우선 RSS 불러오기
        parsingdata = feedparser.parse(feed_lst.RSS)
    except:         #실제로 에러를 내보고 판단하자(우선 RSS주소 미스 정도로는 에러 안 남)
        logger.critical("Error in feedparser.parse, name = " + feed_lst.name)
        raise

    
    try:            #갱신시각 있는지 확인
        dic_RSS = feed_latest[int(feed_lst.index)][0]
        dic_latest = feed_latest[int(feed_lst.index)][1]
        if not dic_RSS == feed_lst.RSS:
            raise KeyError  #같은 index에서 저장된 주소와 불러온 주소가 다르면 필드 갱신
        
    except KeyError:
        
        #가장 최근 게시글 검색
        latest_time = datetime.strptime('15 Oct 1991 17:50:15 +0900', "%d %b %Y %X %z")
        for entry in parsingdata.entries:
            if latest_time < datetime.strptime(entry.published, "%a, %d %b %Y %X %z"):
                latest_time = datetime.strptime(entry.published, "%a, %d %b %Y %X %z")
        
        feed_latest[feed_lst.index]=[feed_lst.RSS, latest_time]
        logger.info("check latest feed in " + feed_lst.name + ", " + latest_time.strftime("%a, %d %b %Y %X %z"))
        
        new_flag = True

    else:
        #print(feed_lst.name)
        #갱신시각과 비교해서 피드에 갱신시각보다 최신자료가 있으면 트위터에 업로드
        latest_time = dic_latest        #기존의 최근 업로드 시각 입력
        parsingdata.entries.reverse()  #엔트리 순서 뒤집기(등록순으로 정렬시에 과거 자료부터 트위터에 올라가게끔)

        for entry in parsingdata.entries:
            if dic_latest < datetime.strptime(entry.published, "%a, %d %b %Y %X %z"):
                new_flag = True         #late.st 파일을 갱신할 필요가 생김
                if latest_time < datetime.strptime(entry.published, "%a, %d %b %Y %X %z"):
                    latest_time = datetime.strptime(entry.published, "%a, %d %b %Y %X %z")
                
                #트위터로 entry.title이랑 entry.link 내보내기
                logger.info("update feed : " + entry.title)
                Write_Tweet(api, feed_lst, entry)
        feed_latest[feed_lst.index][1] = latest_time

    return new_flag



###

def Twitter_Login(filename=DEFAULT_DIR + "/tweetkey.ini"):

    with open(filename, "r", encoding="utf-8-sig") as pathkey:
        text = pathkey.read()
    try:
        ck = re.compile('(?<=consumer_key=").*?(?=")').search(text).group(0)
        cs = re.compile('(?<=consumer_secret=").*?(?=")').search(text).group(0)
        atk = re.compile('(?<=access_token_key=").*?(?=")').search(text).group(0)
        ats = re.compile('(?<=access_token_secret=").*?(?=")').search(text).group(0)
    except:
        raise CustomError(filename + "파일이 제대로 작성되어있지 않습니다")

    return twitter.Api(consumer_key=ck,
        consumer_secret=cs,
        access_token_key=atk,
        access_token_secret=ats)
    

def Write_Tweet(api, feed_lst, entry):

    #######################print(feed_lst.filter, end=' ')
    #######################print(entry.title, end=' ')
    #######################print(re.compile(feed_lst.filter).match(entry.title))
    if re.compile(feed_lst.filter).match(entry.title):      #정규표현식 기반 필터
        entry.title = html.unescape(entry.title)                #특수문자가 포함된 경우 깨져나오는 것 방지
        msg = feed_lst.prefix + "// " + entry.title + feed_lst.suffix
        if len(msg) > 116:
            msg = feed_lst.prefix + "// " + entry.title[:116-len(msg)] + feed_lst.suffix
        msg = msg + " " + entry.link
        try:
            status = api.PostUpdate(msg)
        except twitter.error.TwitterError as ermsg:
            #ermsg.message는 [{'message': 'Status is a duplicate.', 'code': 187}] 꼴로 에러를 뱉어냄
            if ermsg.message[0]['code'] == 187:     #중복된 트윗이면 그냥 건너뜀
                logger.warning("duplicated tweet : " + msg)
                pass
            else:
                raise

######################################실행부######################################

if __name__ == '__main__':

  #로그 선언
    logger = logging.getLogger('myLog')
    logger.setLevel(logging.DEBUG)

    #로그파일 만들 핸들러 선언
    eventHandler = logging.handlers.RotatingFileHandler(DEFAULT_DIR + '/event.log', maxBytes = 1024 * 10, backupCount = 5)
        #10kByte, 5개까지 로그를 저장함
    eventHandler.setLevel(logging.INFO)
    eventHandler.setFormatter(logging.Formatter('%(asctime)s|%(levelname)s > %(message)s'))

    logger.addHandler(eventHandler) #핸들러 로거에 추가

  #메인 함수
    logger.info("Service Start")

    try:
        feed_list = []      #파일에서 RSS 주소랑 관련정보 불러다 리스트로 저장하는 데 씀, 자료형은 <feedlist>
        feed_latest = {}    #이전 갱신시각 확인하는 데 씀, {index : [RSS, latest]}형태로 저장

        feed_list = inputfile(DEFAULT_DIR + '/feeder.ini')
        feed_latest, new_flag = inputdic(DEFAULT_DIR + '/late.st')

        api = Twitter_Login(DEFAULT_DIR + '/tweetkey.ini')

        for i in range(0,len(feed_list)):
            #피드 개수만큼 파싱
            #######################if feed_list[i].index == 190: #디버그용
            #######################    print("시간 다됐어!")
            new_flag = rss2compare(feed_list[i], api) or new_flag

        outputdic(DEFAULT_DIR + '/late.st', feed_latest, new_flag)
    except Exception as exerr:
        logger.critical('Critical Error : ' + exerr.args[0])
    finally:
        logger.info("Service End")
######################################잡설######################################
#앞으로 해야 할 작업

#작업도를 그려보자
#feed.er에서 자료 읽음 -> title별로 자료 정리(text엔 중복있다) -> feedparser 써서 피드 불러오기 ->
#갱신시각이랑 비교해서 피드에 갱신시각보다 최신자료가 있으면 트위터에 업로드
#   기왕이면 오래된 것부터 업로드하고싶은데 어려울라나 파이썬에서 역순으로 루프 돌리기도 가능한가?
#   <변수>.reverser()로 리스트 순서 뒤집기 가능
#-> 업로드가 전부 끝나면 갱신시각 갱신 -> 다음 피드에 반복
#-> 다 돌았으면 다시 처음으로 돌아가던가 좀 쉬었다 돌아가던가 하면 됨
