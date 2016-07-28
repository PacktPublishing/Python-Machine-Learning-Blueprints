from flask import Flask, request, redirect
import twilio.twiml
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

PATH_TO_CSV = 'path/to/file.csv'
df = pd.read_csv(PATH_TO_CSV)

convo = df.iloc[:,0]

clist = []
def qa_pairs(x):
    cpairs = re.findall(": (.*?)(?:$|\n)", x)
    clist.extend(list(zip(cpairs, cpairs[1:])))

convo.map(qa_pairs);

convo_frame = pd.Series(dict(clist)).to_frame().reset_index()
convo_frame.columns = ['q', 'a']

vectorizer = TfidfVectorizer(ngram_range=(1,3))
vec = vectorizer.fit_transform(convo_frame['q'])

@app.route("/", methods=['GET', 'POST'])
def get_response():
    input_str = request.values.get('Body')

    def get_response(q):
        my_q = vectorizer.transform([input_str])
        cs = cosine_similarity(my_q, vec)
        rs = pd.Series(cs[0]).sort_values(ascending=0)
        rsi = rs.index[0]
        return convo_frame.iloc[rsi]['a']

    resp = twilio.twiml.Response()
    if input_str:
        resp.message(get_response(input_str))
        return str(resp)
    else:
        resp.message('Something bad happened here.')
        return str(resp)