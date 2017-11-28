#!/usr/bin/python3

from pyspark.sql import *
from get_features import *
from pyspark.ml.evaluation import RegressionEvaluator
import os
import math

os.environ["PYSPARK_PYTHON"] = "/usr/bin/python3.6"

N_OF_CLUSTERS = 1000   # number of clusters for which mean is being calculated

"""Time related constant: """
TIME_SLOTS_WITHIN_DAY = 144     # day is divided into that number of slots
N_DAYS_JAN = 31
N_DAYS_FEB = 28
N_DAYS_MAR = 31
N_DAYS_APR = 30
N_DAYS_MAY = 31
N_DAYS_JUN = 30
FIRST_DAY_DAY_OF_WEEK = 3   # which day of the week was the first day of the year 2015 (0 - Monday, 1 - Tuesday, etc.)
N_DAYS_TRAIN = N_DAYS_JAN + N_DAYS_FEB + N_DAYS_MAR + N_DAYS_APR + N_DAYS_MAY # number of days used for the learning
N_OF_TIME_SLOTS_TRAIN = N_DAYS_TRAIN * TIME_SLOTS_WITHIN_DAY # number of time slots that are being used for training
N_DAYS_TEST = N_DAYS_JUN
N_OF_TIME_SLOTS_TEST = N_DAYS_TEST * TIME_SLOTS_WITHIN_DAY

spark = SparkSession.builder.master('spark://csit7-master:7077').getOrCreate()
sqlCtx = SQLContext(spark.sparkContext, spark)

errorsRMSE = []
errorsR2 = []

for i in range(N_OF_CLUSTERS):
    (train_features, train_labels), (test_features, test_labels) = get_features_for_cluster(sqlCtx, i)

    if len(test_labels) == 0:
        errorsRMSE.append(-10.0)
        errorsR2.append(-10.0)
        continue

    # init model
    weekday_means = []

    train_labels_features = list(zip(train_labels, train_features))

    # train
    for week_day in range(7):
        demands_of_weekday = list(filter(lambda x: x[1].day_of_week == week_day + 3, train_labels_features))
        demands_of_weekday = list(map(lambda y: y[0], demands_of_weekday))
        if len(demands_of_weekday) == 0:
            weekday_means.append(0.0)
        else:
            weekday_means.append(sum(demands_of_weekday)/len(demands_of_weekday))

    # predict for each set of test features
    predictions = []
    for features in test_features:
        weekday = features.day_of_week - 3
        prediction = weekday_means[weekday]
        predictions.append(prediction)


    # merge actual_demand and predictions to dataframe for RegressionEvaluator
    dataframe = spark.createDataFrame(zip(test_labels, predictions), ["demand", "prediction"])

    """ Evaluation rmse : """
    evaluatorRMSE = RegressionEvaluator(labelCol="demand", predictionCol="prediction", metricName="rmse")
    rmse = evaluatorRMSE.evaluate(dataframe)
    errorsRMSE.append(rmse)
    print("Root Mean Squared Error (RMSE) on test data = %g" % rmse)

    """ Evaluation r2 : """
    evaluatorR2 = RegressionEvaluator(labelCol="demand", predictionCol="prediction", metricName="r2")
    r2 = evaluatorR2.evaluate(dataframe)
    errorsR2.append(r2)
    print("R Squared Error (R2) on test data = %g" % r2)

""" Writing the errors in the files : """
file = open("means_rmse.txt", "w")
file.write("Training set contains " + str(N_DAYS_TRAIN) + " days i.e. "+ str(N_OF_TIME_SLOTS_TRAIN) + " time slots \nTest set contains "+ str(N_DAYS_TEST)+ " days i.e. "+ str(N_OF_TIME_SLOTS_TEST) + " time slots \n")
for errorIndex in range(N_OF_CLUSTERS):
    file.write("RMSE for cluster " + str(errorIndex) + " is " + str(errorsRMSE[errorIndex]) + "\n")
file.close()

file = open("means_r2.txt", "w")
file.write("Training set contains " + str(N_DAYS_TRAIN) + " days i.e. "+ str(N_OF_TIME_SLOTS_TRAIN) + " time slots \nTest set contains "+ str(N_DAYS_TEST)+ " days i.e. "+ str(N_OF_TIME_SLOTS_TEST) + " time slots \n")
for errorIndex in range(N_OF_CLUSTERS):
    file.write("R2 for cluster " + str(errorIndex) + " is " + str(errorsR2[errorIndex]) + "\n")
file.close()
