import pandas as pd, numpy as np, json, math
from math import comb
R='data/reports_csi_strengthening/'
full=pd.read_csv(R+'csi_predictions_full_stratified.csv',
    usecols=['row_index','y_true','y_score','y_pred','Threat/Content Type','Bytes','Packets','Elapsed Time (sec)'])
noo=pd.read_csv(R+'csi_predictions_no_outcome_stratified.csv',usecols=['row_index','y_pred'])
y=full['y_true'].to_numpy(); s=full['y_score'].to_numpy(); p=full['y_pred'].to_numpy()
prev=float(y.mean()); tot=int(y.sum())
def ap(y,s):
    o=np.argsort(-s,kind='mergesort'); yy=y[o]; tp=np.cumsum(yy); fp=np.cumsum(1-yy)
    P=tp/(tp+fp); Rr=tp/tp[-1]; Rp=np.concatenate([[0],Rr[:-1]]); return float(np.sum((Rr-Rp)*P))
def mf1(y,yp):
    def f1(t):
        TP=np.sum((yp==t)&(y==t));FP=np.sum((yp==t)&(y!=t));FN=np.sum((yp!=t)&(y==t))
        P=TP/(TP+FP) if TP+FP else 0;Rr=TP/(TP+FN) if TP+FN else 0
        return 2*P*Rr/(P+Rr) if P+Rr else 0
    return (f1(0)+f1(1))/2
def topk(y,s,k):
    o=np.argsort(-s,kind='mergesort'); return float(y[o][:k].sum())/k
def bcdf(k,n,pp): return sum(comb(n,i)*pp**i*(1-pp)**(n-i) for i in range(0,k+1))
def bis(f,a,b,it=100):
    fa=f(a)
    for _ in range(it):
        m=(a+b)/2;fm=f(m)
        if fa*fm<=0:b=m
        else:a=m;fa=fm
    return (a+b)/2
def cp(k,n,al=0.05):
    lo=0.0 if k==0 else bis(lambda pp:(1-bcdf(k-1,n,pp))-al/2,0,1)
    hi=1.0 if k==n else bis(lambda pp:bcdf(k,n,pp)-al/2,0,1)
    return [round(lo,4),round(hi,4)]
out={'holdout_n':int(len(y)),'prevalence':prev,'positives':tot}
out['consistency']={'AP_full':round(ap(y,s),4),'macroF1_full':round(mf1(y,p),4),
                    'top100_full':topk(y,s,100)}
out['AP_no_skill']=round(prev,4); out['AP_lift_over_chance']=round(ap(y,s)/prev,2)
# McNemar full vs no-outcome
m=full[['row_index']].copy(); m['cf']=(p==y)
mm=m.merge(noo,on='row_index'); 
cn=(mm['y_pred'].to_numpy()==y)  # noo correct (row order preserved by merge on identical order)
cf=mm['cf'].to_numpy()
b=int(np.sum(cf&~cn)); c=int(np.sum(~cf&cn))
chi=(abs(b-c)-1)**2/(b+c) if (b+c)>0 else 0.0
out['mcnemar_full_vs_nooutcome']={'b':b,'c':c,'chi2_cc':round(chi,2),'p_value':math.erfc(math.sqrt(chi/2)) if chi>0 else 1.0}
out['clopper_pearson']={'full_99of100':cp(99,100),'temporal_100of100':cp(100,100)}
# leakage by Threat/Content Type
g=full.groupby('Threat/Content Type')['y_true'].agg(['size','sum']); g['rate']=g['sum']/g['size']
g=g.sort_values('rate',ascending=False).head(8)
out['leakage_by_content_type']=[{'type':str(i),'n':int(r['size']),'pos':int(r['sum']),
   'pos_rate':round(float(r['rate']),4),'share_of_pos':round(float(r['sum']/tot),4)} for i,r in g.iterrows()]
ct=full['Threat/Content Type'].astype(str).str.lower()
flag=(~ct.isin(['end','','nan','none'])).to_numpy()
out['rule_nonbenign_contenttype']={'flagged':int(flag.sum()),
   'precision':round(float(y[flag].mean()),4) if flag.sum() else 0,
   'recall':round(float(y[flag].sum()/tot),4)}
# single-feature ranking baselines
def fr(col):
    v=pd.to_numeric(full[col],errors='coerce').fillna(-1).to_numpy().astype(float)
    return {'AP':round(ap(y,v),4),'top100':topk(y,v,100),'top500':round(topk(y,v,500),4)}
out['single_feature_baselines']={f:fr(f) for f in ['Bytes','Packets','Elapsed Time (sec)']}
out['majority_class']={'macroF1':round(mf1(y,np.zeros_like(y)),4),'positive_recall':0.0}
json.dump(out,open('data/reports_q1audit/q1audit_addons.json','w'),indent=2)
print(json.dumps(out,indent=2))
