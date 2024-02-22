# -*- coding: utf-8 -*-
import pandas as pd


def explode_df(dataframe, column_to_explode, prefix=None):
    df = dataframe.copy()
    exploded_df = df.explode(column_to_explode)
    new_df = pd.json_normalize(exploded_df[column_to_explode])

    if prefix:
        new_df = new_df.add_prefix(f"{prefix}_")

    df.drop(columns=column_to_explode, inplace=True)
    new_df.index = exploded_df.index
    result_df = df.join(new_df)

    return result_df
