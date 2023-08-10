import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

# alpha vintage
import requests
import json
with open("quant_trading/config.json") as f:
    tokenf = json.load(f)
myToken = tokenf['AlphaV_token']
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey='+myToken
r = requests.get(url)
data = r.json()

#import data
tw2330 = local_csv('2330.csv')
tw2330.index =  pd.to_datetime(tw2330.Date)
tw2330 = tw2330.Close.loc['2016-02-21':'2019-02-21'].pct_change()[1:]
tw2330.name='tw2330'
tsm = get_pricing('TSM',  '2016-02-21', '2019-02-21', fields='price').pct_change()[1:]
tsm.index.tz = None
tsm.name = 'tsm'
#check for null value
tsm.isnull().sum()

#OLS
Pair = pd.concat([tw2330, tsm], axis=1).fillna(method='ffill')
x=sm.add_constant(Pair.tw2330)
y=Pair.tsm
coeff=sm.OLS(y,x).fit()
#type(coeff.params)


print coeff.summary()
print coeff.params['tw2330']
#spread
spread = Pair.tsm - coeff.params['tw2330']*Pair.tw2330
spread.plot();
#type(spread)
spread.mean()


#OLS for rolling beta
model=pd.ols(y=y, x=x, window=60) #dataframe的rolling ols
rollbeta=model.beta #顯示rollingx&y,再顯示每一期算出的intercept(beta)
#rolling spread
roll_spread=Pair.tsm-rollbeta['tw2330']*Pair.tw2330
roll_spread=roll_spread.dropna() #drop掉前面rolling後空白的值
roll_spread.plot();
#standardize rolling spread
zscore=(spread-roll_spread.rolling(window=60,center=False).mean())/roll_spread.rolling(window=60,center=False).std()
zscore=zscore.dropna()
zscore.plot();
zscore.name='score'

#trade
pos =pd.concat([Pair.tsm,zscore],axis =1).dropna() 
pos['short'] =np.where(pos.score>2,1,0)
pos['long'] =np.where(pos.score<-2,1,0) 
pos['tsm_f1'] =pos.tsm.shift(-1) #next period 's return 
pos['w_s']= np.where((pos.short==1) & (pos.tsm_f1<0),1,0)  #short是１且next return小於0的w_s就是1
pos['w_l'] =np.where((pos.long ==1) & (pos.tsm_f1<0),1,0)  #long是１且next return小於0的w_s就是1
#print(pos[pos['short']==1])
#print(pos[pos['long']==1])
ret = (pos[pos['short']==1].tsm_f1.mean()*(-1)+pos[pos['long']==1].tsm_f1.mean())
print ret

print 'short odds:',(pos[pos['short']==1].w_s.sum()), (pos[pos['short']==1].short.sum())
print 'long odds:',(pos[pos['long']==1].w_l.sum()), (pos[pos['long']==1].long.sum())

Pair.corr()
cum = Pair.add(1).cumprod().subtract(1)
cum.plot()

#arbit
cum['arbit'] = cum['tsm'] - cum['tw2330']
cum['arbit'].plot()