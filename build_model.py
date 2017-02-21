import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cross_validation import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
plt.style.use('fivethirtyeight')


def load_split_data(filename):
    df = pd.read_pickle(filename)
    df = df.drop(['Mostly Cloudy', 'Clear', 'Partly Cloudy', 'Flurries', \
                  'Light Snow', 'Foggy', 'Snow', 'Rain'], axis=1)
    y = df.pop('prediction').values
    X = df.values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y)
    return df, X_train, X_test, y_train, y_test


def fit_model(X_train, X_test, y_train, y_test):
    model = RandomForestClassifier(n_estimators=50, random_state=0)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print "Accuracy: ", accuracy_score(y_test, y_pred)
    print "Precision: ", precision_score(y_test, y_pred)
    print "Recall: ", recall_score(y_test, y_pred)
    return model

def plot_importances(model, df):
    importance_lst = zip(df.columns, model.feature_importances_)
    importance_lst.sort(key=lambda x: x[1])
    labels = [tup[0] for tup in importance_lst[::-1]]
    importances = [tup[1] for tup in importance_lst[::-1]]

    fig = plt.figure(figsize=(16, 8))
    fig.suptitle('Feature Importances', fontsize=35)
    ax = fig.add_subplot(111)
    ax.bar(range(len(importances)), importances, color='#30a2da')
    ax.set_xlabels=labels
    plt.xticks(range(len(importances)), labels, rotation=60, fontsize=18)
    plt.yticks(fontsize=18)
    plt.savefig('img/feature_importance.png')
    plt.show()


if __name__ == '__main__':
    df, X_train, X_test, y_train, y_test = load_split_data('data/groundhog_hourly_scrubbed.pkl')
    model = fit_model(X_train, X_test, y_train, y_test)
    plot_importances(model, df)
