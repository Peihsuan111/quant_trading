import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm

# import part A data
part_a = pd.read_csv('../data/2330.csv')
part_a.index =  pd.to_datetime(part_a.date)
# part A percentage change of close price 
part_a = part_a.close.loc['2020-01-02':'2023-08-09'].pct_change()[1:]
part_a.name='part_a'

# import part B data
part_b = pd.read_csv('../data/2454.csv')
part_b.index =  pd.to_datetime(part_b.date)
# part B percentage change of close price 
part_b = part_b.close.loc['2020-01-02':'2023-08-09'].pct_change()[1:]
part_b.name = 'part_b'

# check for null value
part_a.isnull().sum()
part_b.isnull().sum()

# 合併part_a & part_b
Pair = pd.concat([part_a, part_b], axis=1).fillna(method='ffill') 

# OLS
x = sm.add_constant(Pair.part_a) # add constant term
y = Pair.part_b
coeff = sm.OLS(y,x).fit() # Create a model
#type(coeff.params)

# Summary
print(coeff.summary())
print(coeff.params['part_a'])
#spread
spread = Pair.part_b - coeff.params['part_a']*Pair.part_a
spread.plot();
#type(spread)
spread.mean()


#OLS for rolling beta
model=pd.ols(y=y, x=x, window=60) #dataframe的rolling ols
rollbeta=model.beta #顯示rollingx&y,再顯示每一期算出的intercept(beta)
#rolling spread
roll_spread=Pair.part_b-rollbeta['part_a']*Pair.part_a
roll_spread=roll_spread.dropna() #drop掉前面rolling後空白的值
roll_spread.plot();
#standardize rolling spread
zscore=(spread-roll_spread.rolling(window=60,center=False).mean())/roll_spread.rolling(window=60,center=False).std()
zscore=zscore.dropna()
zscore.plot();
zscore.name='score'

#trade
pos =pd.concat([Pair.part_b,zscore],axis =1).dropna() 
pos['short'] =np.where(pos.score>2,1,0)
pos['long'] =np.where(pos.score<-2,1,0) 
pos['part_b_f1'] =pos.part_b.shift(-1) #next period 's return 
pos['w_s']= np.where((pos.short==1) & (pos.part_b_f1<0),1,0)  #short是１且next return小於0的w_s就是1
pos['w_l'] =np.where((pos.long ==1) & (pos.part_b_f1<0),1,0)  #long是１且next return小於0的w_s就是1
#print(pos[pos['short']==1])
#print(pos[pos['long']==1])
ret = (pos[pos['short']==1].part_b_f1.mean()*(-1)+pos[pos['long']==1].part_b_f1.mean())
print ret

print 'short odds:',(pos[pos['short']==1].w_s.sum()), (pos[pos['short']==1].short.sum())
print 'long odds:',(pos[pos['long']==1].w_l.sum()), (pos[pos['long']==1].long.sum())

Pair.corr()
cum = Pair.add(1).cumprod().subtract(1)
cum.plot()

#arbit
cum['arbit'] = cum['part_b'] - cum['part_a']
cum['arbit'].plot()