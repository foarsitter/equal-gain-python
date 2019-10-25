import os

import numpy as np
import pandas as pd
from decide import data_folder
from decide.data.database import connection, Manager
from decide.results.helpers import list_to_sql_param

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)


def write_summary_result(conn, model_run_ids, output_directory):
    df = pd.read_sql("""
    SELECT
      a.p as p,
      a.issue as issue,
      a.iteration as iteration,
      a.repetion as repetion,
      a.numerator / a.denominator AS nbs
    FROM (SELECT
            sum(ai.position * ai.power * ai.salience) AS numerator,
            sum(ai.salience * ai.power)               AS denominator,
            r.pointer                                 AS repetion,
            i2.pointer                                AS iteration,
            m.p,
      i.name as issue
          FROM actorissue ai
            LEFT JOIN issue i ON ai.issue_id = i.id
            LEFT JOIN actor a ON ai.actor_id = a.id
            LEFT JOIN iteration i2 ON ai.iteration_id = i2.id
            LEFT JOIN repetition r ON i2.repetition_id = r.id
            LEFT JOIN modelrun m ON r.model_run_id = m.id        
          WHERE  ai.type = 'before' AND m.id IN (%s)
         GROUP BY m.id,r.id, i2.id, i.id) a
    """ % list_to_sql_param(model_run_ids),
                     conn,
                     index_col='p',
                     columns=['nbs']
                     )

    table_avg = pd.pivot_table(df, index=['issue', 'p'], columns=['iteration'], values=['nbs'], aggfunc=np.average)
    table_var = pd.pivot_table(df, index=['issue', 'p'], columns=['iteration'], values=['nbs'], aggfunc=np.var)

    table_avg.to_csv(os.path.join(output_directory, 'nbs_average.csv'))
    table_var.to_csv(os.path.join(output_directory, 'nbs_variance.csv'))

    cursor = conn.execute("""SELECT issue.name, issue.id
FROM issue
INNER JOIN dataset d on issue.data_set_id = d.id
INNER JOIN modelrun m on d.id = m.data_set_id
WHERE m.id IN(%s)
ORDER BY issue.name""" % list_to_sql_param(model_run_ids))
    issues = cursor.fetchall()

    # %%

    for name, issue_id in issues:
        df = pd.read_sql("""SELECT a.p                         as p,
       a.issue                     as issue,
       a.iteration                 as iteration,
       a.repetion                  as repetion,
       a.numerator / a.denominator AS nbs
FROM (SELECT sum(ai.position * ai.power * ai.salience) AS numerator,
             sum(ai.salience * ai.power)
                                                       AS denominator,
             r.pointer
                                                       AS repetion,
             i2.pointer
                                                       AS iteration,
             m.p,
             i.name                                    as issue
      FROM actorissue ai
               LEFT JOIN issue i ON ai.issue_id = i.id
               LEFT JOIN actor a ON ai.actor_id = a.id
               LEFT JOIN iteration i2 ON ai.iteration_id = i2.id
               LEFT JOIN repetition r ON i2.repetition_id = r.id
               LEFT JOIN modelrun m ON r.model_run_id = m.id
               LEFT JOIN dataset d ON a.data_set_id = d.id
      WHERE ai.type = 'before'
        AND m.id = IN (%s)
        AND i.id = ?
      GROUP BY m.id, r.id, i2.id, i.id) a
        """ % list_to_sql_param(model_run_ids),
                         conn,
                         params=[issue_id],
                         index_col='p',
                         columns=['nbs']
                         )
        table = pd.pivot_table(df, index=['iteration'], columns=['p'], values=['nbs'])
        plt = table.plot()
        lgd = plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.title(name)
        plt.ylim(0, 110)

        plt.safe


if __name__ == '__main__':
    m = Manager(os.environ.get('DATABASE_URL'))
    m.init_database()

    model_run_ids = [43, 44]

    write_summary_result(connection, model_run_ids, data_folder)
