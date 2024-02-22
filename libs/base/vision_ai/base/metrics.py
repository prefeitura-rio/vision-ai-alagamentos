# -*- coding: utf-8 -*-
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


# Define a function to handle null values
def calculate_metrics(y_true, y_pred, average):
    # ... (same as before) ...
    # Filter out null values
    valid_indices = y_true.notnull() & y_pred.notnull()
    y_true_filtered = y_true[valid_indices]
    y_pred_filtered = y_pred[valid_indices]

    accuracy = accuracy_score(y_true_filtered, y_pred_filtered)
    precision = precision_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)
    recall = recall_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)
    f1 = f1_score(y_true_filtered, y_pred_filtered, average=average, zero_division=0)

    return accuracy, precision, recall, f1
