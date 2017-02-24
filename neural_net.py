import theano
from keras.utils import np_utils
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.optimizers import SGD, RMSprop, Adagrad, Adam
import pandas as pd
import numpy as np
import cPickle as pickle
from sklearn.cross_validation import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score


def load_split_data(filename):
    df = pd.read_pickle(filename)
    df['prediction'] = df['prediction'].astype(int)
    df = df.drop(['Mostly Cloudy', 'Clear', 'Partly Cloudy', 'Flurries', \
                  'Light Snow', 'Foggy', 'Snow', 'Rain'], axis=1)
    y = df.pop('prediction').values
    X = df.values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)
    return df, X_train, X_test, y_train, y_test


def define_nn_mlp_model(X_train, y_train):
    ''' defines multi-layer-perceptron neural network '''
    model = Sequential()
    model.add(Dense(64, input_dim=X_train.shape[1],
                     init='normal',
                     activation='sigmoid'))
    model.add(Dense(64, init='normal', activation='sigmoid'))
    model.add(Dense(input_dim=64,
                     output_dim=1,
                     init='normal',
                     activation='sigmoid'))
    # sgd = SGD(lr=0.001, decay=1e-7, momentum=0.9, nesterov=True)
    # rms = RMSprop(lr=0.001, rho=0.9, epsilon=1e-08, decay=0.0)
    adam = Adam(lr=0.1, beta_1=0.9, beta_2=0.999, epsilon=1e-08, decay=0.0)
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=["accuracy"] )
    return model


def print_output(model, y_train, y_test, rng_seed):
    '''prints model accuracy results'''
    y_train_pred = model.predict_classes(X_train, verbose=0).squeeze()
    y_test_pred = model.predict_classes(X_test, verbose=0).squeeze()
    # y_train_pred.resize(1, y_train_pred.shape[0])
    print '\nRandom number generator seed: ', rng_seed
    print '\nFirst 20 labels:      ', y_train[:20]
    print 'First 20 predictions: ', y_train_pred[:20]
    train_acc = accuracy_score(y_train, y_train_pred)
    train_prec = precision_score(y_train, y_train_pred)
    train_rec = recall_score(y_train, y_train_pred)
    print '\nTraining accuracy: %.2f%%' % (train_acc * 100), \
    '\nTraining precision: %.2f%%' % (train_prec * 100), \
    '\nTraining recall: %.2f%%' % (train_rec * 100)
    test_acc = accuracy_score(y_test, y_test_pred)
    test_prec = precision_score(y_test, y_test_pred)
    test_rec = recall_score(y_test, y_test_pred)
    print 'Test accuracy: %.2f%%' % (test_acc * 100), \
    '\nTest precision: %.2f%%' % (test_prec * 100), \
    '\nTest recall: %.2f%%' % (test_rec * 100)
    if test_acc < 0.94:
        print '\nMan, your test accuracy is bad!'
    else:
        print "\nYou've made some improvements, I see..."


def pickle_it(model, filename):
    with open('data/{}'.format(filename), 'wb') as f:
        pickle.dump(model, f)


if __name__ == '__main__':

    rng_seed = 42
    df, X_train, X_test, y_train, y_test = load_split_data('data/groundhog_hourly_scrubbed.pkl')
    model = define_nn_mlp_model(X_train, y_train)
    model.fit(X_train, y_train, nb_epoch=35, batch_size=2, verbose=1, validation_split=0.1)
    print_output(model, y_train, y_test, rng_seed)
    pickle_it(model, 'nn_model.pkl')
