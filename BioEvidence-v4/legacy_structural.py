"""Execute the original v1 structural-statements without model generation.

v1 exposes these inside main(), not as a callable scoring function. Extract
their AST from the immutable source instead of maintaining copied formulas.
"""
import ast
from collections import Counter
from common import V1

def structural(rows):
    path=V1/'src/bioevidence/inference/eval_taskb.py'
    module=ast.parse(path.read_text(encoding='utf-8'))
    main=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    loop=next(n for n in main.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Call)
              and isinstance(n.iter.func,ast.Name) and n.iter.func.id=='enumerate')
    statements=[n for n in loop.body if isinstance(n,ast.If) and any(
        isinstance(x,ast.Subscript) and isinstance(x.value,ast.Name) and x.value.id=='stats'
        for x in ast.walk(n))]
    assert len(statements)==3,'Historical structural block changed; stop instead of guessing'
    block=compile(ast.Module(body=statements,type_ignores=[]),str(path),'exec')
    update=next(n.value for n in main.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
        and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name)
        and n.value.func.value.id=='summary' and n.value.func.attr=='update')
    dictionary=update.args[0]
    expr=next(v for k,v in zip(dictionary.keys,dictionary.values)
              if isinstance(k,ast.Constant) and k.value=='citation_structural_checks')
    expression=compile(ast.Expression(body=expr),str(path),'eval')
    env={'stats':Counter()}
    for row in rows:
        env.update(row=row,gold_doc='PMID'+row['question_id'],
            idx_to_doc={int(k):v for k,v in row['idx_to_doc'].items()})
        exec(block,env)
    return eval(expression,env)
