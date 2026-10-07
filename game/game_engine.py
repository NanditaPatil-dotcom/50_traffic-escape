import json
import pygame
import random
from pathlib import Path
from game.player import Player,LANE_W
from game.traffic import Car,make_car

LANES=8
WIDTH=LANES*LANE_W
HEIGHT=600
FPS=60
BG=(60,60,60)
STARTING_LIVES=3
DAY_NIGHT_SECONDS=5
CYCLE_FRAMES=DAY_NIGHT_SECONDS*FPS
RIVER_TOP=250
RIVER_HEIGHT=90
LOG_W=160
LOG_H=46
LOG_SPEED=2.2
HIGH_SCORE_FILE=Path(__file__).resolve().parent.parent/"high_scores.json"

RIVER_RECT=pygame.Rect(0,RIVER_TOP,WIDTH,RIVER_HEIGHT)

class Log:
    def __init__(self,x,y,speed):
        self.x=x
        self.rect=pygame.Rect(x,y,LOG_W,LOG_H)
        self.speed=speed

    def update(self):
        self.x+=self.speed
        self.rect.x=round(self.x)
        if self.speed>0 and self.rect.left>WIDTH:
            self.x=-self.rect.width
            self.rect.x=round(self.x)
        if self.speed<0 and self.rect.right<0:
            self.x=WIDTH
            self.rect.x=round(self.x)

    def draw(self,screen):
        pygame.draw.rect(screen,(140,82,45),self.rect,border_radius=14)
        pygame.draw.rect(screen,(105,58,34),self.rect.inflate(-18,-16),border_radius=10)
        for x in range(self.rect.left+28,self.rect.right-20,44):
            pygame.draw.line(screen,(86,46,28),(x,self.rect.top+8),(x,self.rect.bottom-8),3)

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen=pygame.display.set_mode((WIDTH,HEIGHT))
        pygame.display.set_caption("Traffic Escape")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("monospace",24,bold=True)
        self.big_font=pygame.font.SysFont("monospace",44,bold=True)
        self.high_scores=self._load_high_scores()
        self.reset()

    def reset(self):
        self.player=Player(WIDTH//2,HEIGHT-80)
        self.cars=[]
        self.logs=self._make_logs()
        self.timer=0
        self.spawn_interval=50
        self.speed=3
        self.score=0
        self.lives=STARTING_LIVES
        self.hit_cooldown=0
        self.score_saved=False
        self.cycle_timer=0
        self.is_night=False
        self.game_over=False
        self.won=False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type==pygame.QUIT: return False
            if event.type==pygame.KEYDOWN and event.key==pygame.K_r: self.reset()
        return True

    def update(self):
        if self.game_over or self.won: return
        keys=pygame.key.get_pressed()
        self.player.move(keys,0,WIDTH)
        if self.hit_cooldown>0:
            self.hit_cooldown-=1
        self.cycle_timer+=1
        if self.cycle_timer>=CYCLE_FRAMES:
            self.cycle_timer=0
            self.is_night=not self.is_night
        self.timer+=1
        for log in self.logs:
            log.update()
        self._check_river_crossing()
        if self.game_over:
            return
        if self.timer>=self.spawn_interval:
            lane=random.randint(0,LANES-1)
            self.cars.append(make_car(lane,HEIGHT,self.speed))
            self.timer=0
            self.spawn_interval=max(22,self.spawn_interval-0.2)
        for c in self.cars:
            c.update()
            if self.hit_cooldown==0 and not self._player_in_river() and c.rect.colliderect(self.player.rect):
                self._handle_player_hit()
                break
        self.cars=[c for c in self.cars if not c.off_screen(HEIGHT)]
        self.score+=1
        if self.score%300==0: self.speed=min(10,self.speed+0.5)
        if self.player.rect.top<=10:
            self.won=True
            self._record_score()

    def draw(self):
        road_color=(60,60,60) if not self.is_night else (20,24,34)
        lane_color=(100,100,100) if not self.is_night else (70,78,95)
        divider_color=(200,200,100) if not self.is_night else (180,170,90)
        sidewalk_color=(150,130,110) if not self.is_night else (82,76,90)
        water_color=(35,95,150) if not self.is_night else (12,42,76)
        wave_color=(88,150,205) if not self.is_night else (48,92,135)
        self.screen.fill(road_color)
        # road markings
        for i in range(LANES+1):
            pygame.draw.line(self.screen,lane_color,(i*LANE_W,0),(i*LANE_W,HEIGHT),2)
        for y in range(0,HEIGHT,60):
            for i in range(LANES):
                pygame.draw.rect(self.screen,divider_color,pygame.Rect(i*LANE_W+LANE_W//2-3,y,6,30))
        # sidewalks
        pygame.draw.rect(self.screen,sidewalk_color,pygame.Rect(0,HEIGHT-50,WIDTH,50))
        pygame.draw.rect(self.screen,sidewalk_color,pygame.Rect(0,0,WIDTH,30))
        for c in self.cars: c.draw(self.screen,self.is_night)
        pygame.draw.rect(self.screen,water_color,RIVER_RECT)
        for wave_y in range(RIVER_TOP+14,RIVER_TOP+RIVER_HEIGHT,24):
            pygame.draw.line(self.screen,wave_color,(0,wave_y),(WIDTH,wave_y),2)
        for log in self.logs: log.draw(self.screen)
        self.player.draw(self.screen)
        hud=pygame.Rect(0,0,WIDTH,30)
        pygame.draw.rect(self.screen,(20,20,20),hud)
        mode="NIGHT" if self.is_night else "DAY"
        s=self.font.render(f"{mode}  Lives: {self.lives}  Score: {self.score//10}  GOAL: reach the top!  R=Restart",True,(220,220,220))
        self.screen.blit(s,(6,4))
        if self.game_over:
            self._msg("CRASHED!",(220,60,60))
        if self.won:
            self._msg("YOU MADE IT!",(80,220,80))
        pygame.display.flip()

    def _msg(self,text,color):
        ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        ov.fill((0,0,0,150))
        self.screen.blit(ov,(0,0))
        m=self.big_font.render(text,True,color)
        sub=self.font.render("Press R to Restart",True,(200,200,200))
        self.screen.blit(m,(WIDTH//2-m.get_width()//2,HEIGHT//2-40))
        self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,HEIGHT//2+20))
        self._draw_high_scores(HEIGHT//2+70)

    def _handle_player_hit(self):
        self.lives-=1
        if self.lives<=0:
            self.game_over=True
            self._record_score()
            return
        self.player=Player(WIDTH//2,HEIGHT-80)
        self.cars=[]
        self.logs=self._make_logs()
        self.hit_cooldown=60

    def _make_logs(self):
        log_y=RIVER_TOP+(RIVER_HEIGHT-LOG_H)//2
        return [
            Log(-40,log_y,LOG_SPEED),
            Log(220,log_y,LOG_SPEED),
            Log(480,log_y,LOG_SPEED),
        ]

    def _check_river_crossing(self):
        if self.hit_cooldown>0 or not self._player_in_river():
            return
        for log in self.logs:
            if log.rect.colliderect(self.player.rect):
                self.player.rect.x+=round(log.speed)
                self.player.rect.x=max(0,min(WIDTH-self.player.rect.width,self.player.rect.x))
                return
        self._handle_player_hit()

    def _player_in_river(self):
        return RIVER_RECT.collidepoint(self.player.rect.center)

    def _current_score(self):
        return self.score//10

    def _record_score(self):
        if self.score_saved:
            return
        self.score_saved=True
        score=self._current_score()
        self.high_scores=sorted(self.high_scores+[score],reverse=True)[:5]
        HIGH_SCORE_FILE.write_text(json.dumps(self.high_scores,indent=2)+"\n")

    def _load_high_scores(self):
        if not HIGH_SCORE_FILE.exists():
            return []
        try:
            scores=json.loads(HIGH_SCORE_FILE.read_text())
        except (OSError,json.JSONDecodeError):
            return []
        if not isinstance(scores,list):
            return []
        clean_scores=[score for score in scores if isinstance(score,int)]
        return sorted(clean_scores,reverse=True)[:5]

    def _draw_high_scores(self,y):
        title=self.font.render("HIGH SCORES",True,(240,220,120))
        self.screen.blit(title,(WIDTH//2-title.get_width()//2,y))
        if not self.high_scores:
            empty=self.font.render("No scores yet",True,(210,210,210))
            self.screen.blit(empty,(WIDTH//2-empty.get_width()//2,y+30))
            return
        for idx,score in enumerate(self.high_scores,1):
            row=self.font.render(f"{idx}. {score}",True,(230,230,230))
            self.screen.blit(row,(WIDTH//2-row.get_width()//2,y+idx*28))

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
