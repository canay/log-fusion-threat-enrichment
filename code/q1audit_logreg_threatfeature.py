import pandas as pd, numpy as np, json, time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
t0=time.time()
df=pd.read_csv('data/processed/traffic_has_linked_threat_sample.csv')
df.columns=[c.strip() for c in df.columns]
y=df['has_linked_threat'].astype(int).to_numpy()
sid=df['Session ID'].copy()
drop=['has_linked_threat','Session ID','Receive Time','Generate Time','High Res Timestamp']
X=df.drop(columns=[c for c in drop if c in df.columns])
base_feat=list(X.columns)
def enc(tr,te,cols):
    Atr=np.empty((len(tr),len(cols)),np.float32);Ate=np.empty((len(te),len(cols)),np.float32)
    for j,c in enumerate(cols):
        s=tr[c]
        if s.dtype==object:
            cats={v:i for i,v in enumerate(s.astype(str).unique())}
            Atr[:,j]=s.astype(str).map(cats).fillna(-1); Ate[:,j]=te[c].astype(str).map(cats).fillna(-1)
        else:
            m=pd.to_numeric(s,errors='coerce').median()
            Atr[:,j]=pd.to_numeric(s,errors='coerce').fillna(m); Ate[:,j]=pd.to_numeric(te[c],errors='coerce').fillna(m)
    return Atr,Ate
def ap(y,s):
    o=np.argsort(-s,kind='mergesort');yy=y[o];tp=np.cumsum(yy);fp=np.cumsum(1-yy)
    P=tp/(tp+fp);R=tp/tp[-1];Rp=np.concatenate([[0],R[:-1]]);return float(np.sum((R-Rp)*P))
def mf1(y,yp):
    def f1(t):
        TP=np.sum((yp==t)&(y==t));FP=np.sum((yp==t)&(y!=t));FN=np.sum((yp!=t)&(y==t))
        P=TP/(TP+FP) if TP+FP else 0;R=TP/(TP+FN) if TP+FN else 0
        return 2*P*R/(P+R) if P+R else 0
    return (f1(0)+f1(1))/2
def topk(y,s,k):
    o=np.argsort(-s,kind='mergesort');return float(y[o][:k].sum())/k
idx=np.arange(len(y)); itr,ite=train_test_split(idx,test_size=0.2,random_state=42,stratify=y)
Xtr,Xte=X.iloc[itr],X.iloc[ite]; ytr,yte=y[itr],y[ite]
out={'sample_n':int(len(y)),'sample_pos':int(y.sum()),'holdout_n':int(len(ite)),'holdout_pos':int(yte.sum())}
# logistic baseline
Atr,Ate=enc(Xtr,Xte,base_feat); sc=StandardScaler().fit(Atr)
lr=LogisticRegression(max_iter=500,class_weight='balanced',n_jobs=-1).fit(sc.transform(Atr),ytr)
s=lr.predict_proba(sc.transform(Ate))[:,1]
out['logreg_sample']={'macro_f1':round(mf1(yte,(s>=0.5).astype(int)),4),'average_precision':round(ap(yte,s),4),'top100':topk(yte,s,100)}
# no-threat-feature reference (HistGBM, traffic-only) on same split
hg=HistGradientBoostingClassifier(max_iter=300,learning_rate=0.08,max_depth=6,random_state=42).fit(Atr,ytr)
s2=hg.predict_proba(Ate)[:,1]
out['histgbm_traffic_only']={'macro_f1':round(mf1(yte,(s2>=0.5).astype(int)),4),'average_precision':round(ap(yte,s2),4),'top100':topk(yte,s2,100)}
# threat-as-feature: join threat.csv attributes by Session ID
th=pd.read_csv('data/restricted_source_data/raw/threat.csv',usecols=lambda c:c.strip() in ['Session ID','Severity','Threat/Content Name','Category'])
th.columns=[c.strip() for c in th.columns]
sevmap={'informational':1,'low':2,'medium':3,'high':4,'critical':5}
th['sev']=th['Severity'].astype(str).str.lower().map(sevmap).fillna(0)
agg=th.groupby('Session ID').agg(threat_sev=('sev','max'),threat_named=('Threat/Content Name',lambda x:int(x.notna().any()))).reset_index()
m=pd.DataFrame({'Session ID':sid.values}); m=m.merge(agg,on='Session ID',how='left')
m['threat_sev']=m['threat_sev'].fillna(0); m['threat_named']=m['threat_named'].fillna(0)
Xtf=X.copy(); Xtf['threat_sev']=m['threat_sev'].values; Xtf['threat_named']=m['threat_named'].values
tf_feat=base_feat+['threat_sev','threat_named']
Atr2,Ate2=enc(Xtf.iloc[itr],Xtf.iloc[ite],tf_feat)
hg2=HistGradientBoostingClassifier(max_iter=300,learning_rate=0.08,max_depth=6,random_state=42).fit(Atr2,ytr)
s3=hg2.predict_proba(Ate2)[:,1]
out['histgbm_threat_as_feature']={'macro_f1':round(mf1(yte,(s3>=0.5).astype(int)),4),'average_precision':round(ap(yte,s3),4),'top100':topk(yte,s3,100)}
out['secs']=round(time.time()-t0,1)
json.dump(out,open('data/reports_q1audit/t_sample.json','w'),indent=2)
print(json.dumps(out,indent=2))
