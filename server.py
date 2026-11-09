import os, json, sqlite3, secrets, time, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timezone

BASE=Path(__file__).resolve().parent
DB=Path(os.environ.get('GAME_DB', str(BASE/'game.sqlite3')))
ADMIN=os.environ.get('GAME_ADMIN_PASSWORD','')
PORT=int(os.environ.get('PORT','8000'))
LOCK=threading.RLock()
R1=['Tháp Bà Pô-na-ga ở đâu?','Tháp Bà Pô-na-ga là một địa điểm du lịch thuộc tỉnh Khánh Hòa.','Ông ngoại đưa đón Dương đi học mỗi khi bố mẹ bận rộn.','Mỗi một ngày trôi qua, ông đang già đi, còn nó mạnh mẽ hơn.','Ông ngoại ơi, cháu yêu ông nhiều lắm!']
R2=[R1[1],R1[2],R1[3]]
GROUPS=['Câu giới thiệu sự vật','Câu nêu hoạt động','Câu nêu đặc điểm']

def conn():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init():
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY CHECK(id=1), epoch INTEGER NOT NULL)')
        c.execute('INSERT OR IGNORE INTO meta VALUES(1,1)')
        c.execute('''CREATE TABLE IF NOT EXISTS teams (id TEXT PRIMARY KEY, epoch INTEGER NOT NULL, name TEXT NOT NULL, created REAL NOT NULL, r1_start REAL NOT NULL, r1_end REAL, r2_start REAL, r2_end REAL, r1_points INTEGER DEFAULT 0, r2_points INTEGER DEFAULT 0, r1_first INTEGER DEFAULT 0, finished INTEGER DEFAULT 0)''')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS team_name_epoch ON teams(epoch, name COLLATE NOCASE)')

def epoch(c): return c.execute('SELECT epoch FROM meta WHERE id=1').fetchone()['epoch']
def ranking(c):
    e=epoch(c)
    rows=c.execute('SELECT name,r1_points,r2_points,r1_start,r1_end,r2_start,r2_end FROM teams WHERE epoch=? AND finished=1',(e,)).fetchall()
    result=[]
    for r in rows:
        elapsed=round((r['r1_end']-r['r1_start'])+(r['r2_end']-r['r2_start']),3)
        result.append(dict(name=r['name'],r1=r['r1_points'],r2=r['r2_points'],total=r['r1_points']+r['r2_points'],seconds=elapsed))
    result.sort(key=lambda x:(-x['total'],x['seconds'],x['name'].casefold()))
    for i,x in enumerate(result): x['rank']=1+sum(1 for y in result if y['total']>x['total'] or (y['total']==x['total'] and y['seconds']<x['seconds']))
    return result

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(BASE),**kwargs)
    def log_message(self,fmt,*args): print('%s %s'%(self.address_string(),fmt%args),flush=True)
    def send_json(self,code,data):
        b=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def read_json(self):
        if int(self.headers.get('Content-Length','0'))>12000: raise ValueError('Dữ liệu quá lớn')
        return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/api/leaderboard':
            with LOCK,conn() as c: self.send_json(200,dict(epoch=epoch(c),ranking=ranking(c),server_time=time.time()))
            return
        if p=='/api/health': self.send_json(200,{'ok':True});return
        if p=='/': self.path='/index.html'
        return super().do_GET()
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            d=self.read_json()
            with LOCK,conn() as c:
                now=time.time(); e=epoch(c)
                if p=='/api/join':
                    name=str(d.get('name','')).strip()
                    if not 1<=len(name)<=35: return self.send_json(400,{'error':'Tên nhóm phải có từ 1 đến 35 ký tự.'})
                    sid=secrets.token_urlsafe(24)
                    try: c.execute('INSERT INTO teams(id,epoch,name,created,r1_start) VALUES(?,?,?,?,?)',(sid,e,name,now,now))
                    except sqlite3.IntegrityError: return self.send_json(409,{'error':'Tên nhóm đã được sử dụng trong đợt thi này.'})
                    return self.send_json(200,{'token':sid,'epoch':e,'name':name})
                if p=='/api/reset':
                    if not ADMIN or not secrets.compare_digest(str(d.get('password','')),ADMIN):return self.send_json(403,{'error':'Mật khẩu quản lý không đúng hoặc chưa cấu hình.'})
                    c.execute('UPDATE meta SET epoch=epoch+1 WHERE id=1')
                    return self.send_json(200,{'ok':True,'epoch':epoch(c)})
                if p in ('/api/round1','/api/round2'):
                    token=str(d.get('token',''))
                    row=c.execute('SELECT * FROM teams WHERE id=? AND epoch=?',(token,e)).fetchone()
                    if not row:return self.send_json(403,{'error':'Phiên chơi không hợp lệ hoặc đợt thi đã kết thúc.'})
                    if p=='/api/round1':
                        if row['r1_end'] is not None:return self.send_json(409,{'error':'Vòng 1 đã hoàn thành.'})
                        selected=d.get('selected',[])
                        if not isinstance(selected,list) or any(type(x)!=int or x not in range(5) for x in selected):return self.send_json(400,{'error':'Đáp án không hợp lệ.'})
                        chosen=set(selected); correct={1,2,3}; passed=chosen==correct
                        points=10*sum((i in chosen)==(i in correct) for i in range(5))
                        if not row['r1_first']:
                            c.execute('UPDATE teams SET r1_first=1,r1_points=? WHERE id=?',(points,token))
                        if passed:c.execute('UPDATE teams SET r1_end=?,r2_start=? WHERE id=?',(now,now,token))
                        return self.send_json(200,{'passed':passed,'first_points':points if not row['r1_first'] else row['r1_points'],'message':'Chính xác! Mở khóa vòng 2.' if passed else 'Chưa đúng, hãy chọn lại các câu kể.'})
                    if row['r1_end'] is None:return self.send_json(403,{'error':'Cần hoàn thành vòng 1 trước.'})
                    if row['finished']:return self.send_json(409,{'error':'Vòng 2 đã nộp, không thể làm lại.'})
                    answers=d.get('answers',{})
                    if not isinstance(answers,dict) or any(k not in ('0','1','2') or type(v)!=int or v not in (0,1,2) for k,v in answers.items()):return self.send_json(400,{'error':'Phân loại không hợp lệ.'})
                    points=20*sum(answers.get(str(i))==i for i in range(3))
                    c.execute('UPDATE teams SET r2_points=?,r2_end=?,finished=1 WHERE id=?',(points,now,token))
                    r=c.execute('SELECT * FROM teams WHERE id=?',(token,)).fetchone()
                    elapsed=round((r['r1_end']-r['r1_start'])+(r['r2_end']-r['r2_start']),2)
                    return self.send_json(200,{'r1':r['r1_points'],'r2':points,'total':r['r1_points']+points,'seconds':elapsed,'ranking':ranking(c)})
                return self.send_json(404,{'error':'Không tìm thấy chức năng.'})
        except (ValueError,json.JSONDecodeError) as exc:self.send_json(400,{'error':str(exc)})
        except Exception as exc:
            print('SERVER ERROR',repr(exc),flush=True)
            self.send_json(500,{'error':'Máy chủ gặp lỗi. Vui lòng thử lại.'})

if __name__=='__main__':
    init();print(f'Game running on 0.0.0.0:{PORT}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
