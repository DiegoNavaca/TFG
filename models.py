import joblib
import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.metrics import roc_auc_score
from sklearn.svm import OneClassSVM
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from itertools import product
from sklearn.decomposition import PCA
from keras.models import load_model
from os.path import exists

from data import get_Range_Descriptors
from data import prepare_Hist_and_Labels

def train_and_Test(training, test, video_classification, params_training, bins_vals, encoder_dir, verbose = 0, eliminar_descriptores = []):    
    acc_list = []
    auc_list = []
    params_list = []

    range_max, range_min = get_Range_Descriptors(training, video_classification)

    for n_bins in bins_vals:
        hist, labels = prepare_Hist_and_Labels(training, range_max,range_min,
                                               video_classification, n_bins, eliminar_descriptores, eliminar_vacios = True)
        
        hist_test, labels_test = prepare_Hist_and_Labels(test, range_max,range_min,
                                                         video_classification, n_bins, eliminar_descriptores)
        
        # pca = PCA(n_components=0.95)
        # pca.fit(hist)
        # hist = pca.transform(hist)
        # hist_test = pca.transform(hist_test)
        encoder_file = encoder_dir+"encoder"+str(n_bins)+".h5"
        try:
            encoder = load_model(encoder_file, compile=False)
            #encoder.compile(optimizer='adam', loss='mean_squared_error')
            hist = encoder.predict(np.array(hist))
            hist_test = encoder.predict(np.array(hist_test))
        except:
            print("Error al codificar, continuando con histogramas normales")

        if "hidden_layer_sizes" in params_training:
            keys, values = zip(*params_training.items())
            permutations_dicts = [dict(zip(keys, v)) for v in product(*values)]
            for params in permutations_dicts:
                model = train_Network(hist, labels, params)

                prediction = test_model(hist_test, model, video_classification)

                acc = accuracy_score(labels_test,prediction)
                
                params_list.append(dict({"n_bins":n_bins},**params))
                try:
                    auc = roc_auc_score(labels_test,prediction)
                except:
                    auc = 0

                acc_list.append(acc)
                auc_list.append(auc)
                    
                if verbose > 0:
                    print("ACC: {:1.2f} - AUC: {:1.2f} - {}".format(acc, auc, params))
            
        elif "C" in params_training:
            for C in params_training["C"]:
                model = train_SVC(hist,labels,C)

                prediction = test_model(hist_test, model, video_classification)

                acc = accuracy_score(labels_test,prediction)
                
                params_list.append({"n_bins":n_bins,"C":C})
                try:
                    auc = roc_auc_score(labels_test,prediction)
                except:
                    auc = 0

                acc_list.append(acc)
                auc_list.append(auc)
                    
                if verbose > 0:
                    print("ACC: {:1.2f} - AUC: {:1.2f} - {}".format(acc, auc, params_list[-1]))

    return acc_list, auc_list, params_list

def train_OC_SVM(samples, nu = 0.1, out_file = None):
    svm = OneClassSVM(nu = nu, verbose = False, kernel = "sigmoid").fit(samples)
    if out_file is not None:
        joblib.dump(svm, out_file)

    return svm

def train_SVC(samples, labels, C = 10, out_file = None):
    svm = SVC(C = C, kernel = "rbf", decision_function_shape = 'ovo', class_weight = 'balanced')
    svm.fit(samples, labels)
    if out_file is not None:
        joblib.dump(svm, out_file)

    return svm
    

def train_Network(samples, labels, params, out_file = None):
    model = MLPClassifier(max_iter = 2000, **params)

    model.fit(samples,labels)

    if out_file is not None:
        joblib.dump(model, out_file)

    return model

def test_model(samples, model, video_classification):
    prediction = model.predict(samples)

    if not video_classification:    
        prediction = [1 if not samples[i].any() else prediction[i] for i in range(len(prediction))]

    return prediction
