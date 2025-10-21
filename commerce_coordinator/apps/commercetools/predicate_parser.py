"""
Predicate Parser for Commercetools Cart Predicates

Overview:
---------
This parser evaluates Commercetools cart predicates used in discount codes.
It uses a grammar-based approach with the Lark library to parse and handle
complex predicate expressions. It supports:

- Logical operations (AND, OR) e.g. quantity = 1 and attributes.mode = "verified"
- Comparison operations (=, !=, >, <, >=, <=) e.g. product.key = "TestX+CS101
- Field access with dot notation e.g. product.key, attributes.`course-key`
- List membership checks (in, not in) e.g. attributes.mode in ("verified", "professional")
- Existence checks (is defined, is not defined) e.g. custom.bundleId is defined
- Complex expressions: Nested parentheses and multiple conditions
- Specific function call: `lineItemCount(expression) = 1`

Key Components:
--------------
3. Grammar definition: Lark grammar for predicate syntax
1. PredicateTransformer: Transforms parsed AST into evaluable expressions
2. CartPredicateParser: Main parser class with evaluation logic

Context Structure and Limitations:
---------------------------------
It currently supports evaluation of predicates against a limited context structure.
The context is generated from Commercetools product and variant data with these fields:

{
    'quantity': 1,  # Fixed value, always 1
    'custom': {'bundleId': None},  # Fixed value, always None
    'product': {'id': product.id, 'key': product.key} # only key and id of product
    'variant': {'sku': variant.key, 'key': variant.sku} # only sku and key of variant
    'attributes': {attribute_name: attribute_value, ...} # all attributes of the variant
}

Note: The current implementation only supports these specific fields.
To support additional fields, the create_context_from_ct_product_and_variant
method would need to be updated to include those fields in the context dictionary.

Debug Mode:
----------
The parser includes a debug mode that provides colorized output showing
the evaluation process and intermediate results, useful for troubleshooting
complex predicate expressions.The red and green color coding indicates
the success or failure of each evaluation step.

Debug mode can be enabled by passing `debug=True` to the `check` method

Usage Example:
-------------
```python
parser = CartPredicateParser()
context = parser.create_context_from_ct_product_and_variant(
    product=product_projection,
    product_variant=variant
)
result = parser.check(
    predicate='quantity = 1 and attributes.mode = "verified"',
    context=context
)
```
"""

from functools import reduce
from operator import getitem

from commercetools.platform.models import ProductProjection, ProductVariant
from lark import Lark, Transformer, v_args


@v_args(inline=True)
class PredicateTransformer(Transformer):
    """Transformer for parsing and transforming predicates in Commercetools."""

    def backtick_name(self, token):
        """Handles backtick names in predicates."""
        return token

    def dotted_name(self, *parts):
        """Handles dotted names in predicates."""
        return ".".join(str(part) for part in parts)

    def function_call(self, name, args=None):
        """Handles function calls in predicates."""
        return ("func", str(name), args or [])

    def args(self, *args):
        """Handles arguments in function calls."""
        return list(args)

    def field(self, f):
        """Handles fields in predicates."""
        return f

    def comparison(self, field, op, value):
        """Handles comparisons in predicates."""
        return ("cmp", str(op), field, value)

    def and_expr(self, a, b):
        """Handles 'and' expressions in predicates."""
        return ("and", a, b)

    def or_expr(self, a, b):
        """Handles 'or' expressions in predicates."""
        return ("or", a, b)

    def list_(self, *items):
        """Handles lists in predicates."""
        return list(items)

    def start(self, expr):
        """Handles the start of the predicate expression."""
        return expr

    def is_defined_expr(self, field, not_token=None):
        """Handles 'is defined' expressions in predicates."""
        negate = False
        if not_token and str(not_token) == "not":
            negate = True
        return ("is_defined", field, negate)

    def in_expr(self, field, *tokens):
        """Handles 'in' expressions in predicates."""
        items = []
        negate = False
        for token in tokens:
            if isinstance(token, list):
                items = token
            elif str(token) == "not":
                negate = True

        return ("in_expr", field, items, negate)

    def value(self, v):
        """Handles values in predicates."""
        if hasattr(v, "children"):
            return self.transform(v.children[0])
        else:
            if v.type == "ESCAPED_STRING":
                return v.value[1:-1]
            elif v.type == "SIGNED_NUMBER":
                return float(v.value)
            else:
                return v.value


class CartPredicateParser:
    """Parser for Commercetools Cart predicates."""

    grammar = r"""
        ?start: expr

        ?expr: expr "or" term   -> or_expr
             | term

        ?term: term "and" factor -> and_expr
             | factor

        ?factor: "(" expr ")"
               | comparison

        comparison: field OP value
                  | field NOT? "in" list_      -> in_expr
                  | field "is" NOT? "defined"  -> is_defined_expr

        field: function_call | dotted_name
        dotted_name: CNAME ("." (CNAME | backtick_name))*
        backtick_name: "`" /[^`]+/ "`"

        function_call: CNAME "(" args? ")"
        args: expr ("," expr)*

        list_: "(" [value ("," value)*] ")"

        OP: "=" | "!=" | ">" | "<" | ">=" | "<="

        NOT: "not"

        value: ESCAPED_STRING | SIGNED_NUMBER | CNAME

        %import common.CNAME
        %import common.ESCAPED_STRING
        %import common.SIGNED_NUMBER
        %import common.WS
        %ignore WS
    """

    def __init__(self):
        self.parser = Lark(self.grammar, parser="lalr")
        self.transformer = PredicateTransformer()

    def create_context_from_ct_product_and_variant(
        self, *, product: ProductProjection, product_variant: ProductVariant
    ) -> dict:
        """Create a context dictionary to be used by the parser from Commercetools product and variant."""
        if product_variant.attributes:
            attributes = {
                attribute.name: (
                    attribute.value["key"]
                    if isinstance(attribute.value, dict) and "key" in attribute.value
                    else attribute.value
                )
                for attribute in product_variant.attributes
            }
        else:
            attributes = {}

        return {
            "quantity": 1,
            "custom": {"bundleId": None},
            "product": {
                "id": product.id,
                "key": product.key,
            },
            "variant": {
                "sku": product_variant.key,
                "key": product_variant.sku,
            },
            "attributes": attributes,
        }

    def check(self, *, predicate: str, context: dict, debug=False) -> bool:
        """
        Check if the predicate evaluates to True or False based on the provided context.

        Args:
            predicate (str): The predicate to evaluate.
            context (dict): The context to use for evaluation.
            debug (bool): If True, prints debug output.

        Returns:
            bool: The result of the predicate evaluation.
        """
        self.context = context  # pylint: disable=attribute-defined-outside-init
        parsed_tree = self.parser.parse(predicate)
        transformed_expression = self.transformer.transform(parsed_tree)

        if debug:  # pragma: no cover
            result, debug_output = self._evaluate_with_debug_output(
                transformed_expression
            )
            print(debug_output)
        else:
            result = self._evaluate(transformed_expression)

        # clear context after evaluation
        self.context = None  # pylint: disable=attribute-defined-outside-init
        if not isinstance(result, bool):
            raise ValueError(
                f"Predicate evaluation must return a boolean, got {result}"
            )

        return result

    def _colorize(self, line: str, result: bool) -> str:
        color = "\033[92m" if result else "\033[91m"
        return color + line + "\033[0m"

    def _get_value(self, path):
        keys = path.split(".")
        return reduce(getitem, keys, self.context)

    def _evaluate(self, expression):
        """
        Evaluate the expression.

        Args:
            expression (tuple): The expression to evaluate.

        Returns:
            bool: The result of the evaluation.
        """
        kind, *params = expression

        if kind == "cmp":  # pragma: no cover
            operator, expression, expected = params

            if expected == "true":
                expected = 1
            elif expected == "false":
                expected = 0

            if isinstance(expression, tuple) and expression[0] == "func":
                evaluated = self._evaluate(expression)
            else:
                evaluated = self._get_value(expression)

            if operator == "=":
                result = evaluated == expected
            elif operator == "!=":
                result = evaluated != expected
            elif operator == ">":
                result = evaluated > expected
            elif operator == "<":
                result = evaluated < expected
            elif operator == ">=":
                result = evaluated >= expected
            elif operator == "<=":
                result = evaluated <= expected
            else:
                raise ValueError(f"Unknown operator: {operator}")

            return result

        elif kind == "in_expr":
            field, items, negate = params
            evaluated = self._get_value(field)

            if negate:
                return evaluated not in items
            else:
                return evaluated in items

        elif kind == "is_defined":
            field, negate = params

            if negate:
                return self._get_value(field) is None
            else:
                return self._get_value(field) is not None

        elif kind in ("and", "or"):
            left = self._evaluate(params[0])
            right = self._evaluate(params[1])

            if kind == "and":
                return left and right
            else:
                return left or right

        elif kind == "func":
            name, args = params
            if name in ("lineItemCount", "lineItemExists"):
                if not args:
                    raise ValueError(f"Function {name} called with no arguments")

                result = self._evaluate(args[0])

                if result:
                    return 1
                else:
                    return 0
            else:
                raise ValueError(f"Function {name} not implemented")

        else:
            raise ValueError(f"Unknown expression type: {kind} with params {params}")

    def _evaluate_with_debug_output(
        self, expression, depth=0
    ):  # pragma: no cover  pylint: disable=too-many-statements
        """
        Evaluate the expression with debug output.

        Raises less exceptions and provides more context in the output.
        Greens output if the expression evaluates to True, and reds it if it evaluates to False.
        AND or OR keywords color indicate the result of the operation.

        Args:
            expression (tuple): The expression to evaluate.
            depth (int): The current depth of the evaluation for formatting.

        Returns:
            tuple: A tuple containing the result of the evaluation and a debug output string.
        """
        kind, *params = expression

        if kind == "cmp":
            operator, expression, expected = params

            if expected == "true":
                expected = 1
            elif expected == "false":
                expected = 0

            if isinstance(expression, tuple) and expression[0] == "func":
                evaluated, debug_output = self._evaluate_with_debug_output(
                    expression, depth + 1
                )
            else:
                evaluated, debug_output = self._get_value(expression), None

            if operator == "=":
                result = evaluated == expected
            elif operator == "!=":
                result = evaluated != expected
            elif operator == ">":
                result = evaluated > expected
            elif operator == "<":
                result = evaluated < expected
            elif operator == ">=":
                result = evaluated >= expected
            elif operator == "<=":
                result = evaluated <= expected
            else:
                raise ValueError(f"Unknown operator: {operator}")

            if debug_output:
                colorized = self._colorize(
                    f"{evaluated} {operator} {expected}", result
                )
                debug_output += f"\n{colorized}"
            else:
                debug_output = self._colorize(
                    f"{expression} {operator} {expected}", result
                )

            return result, debug_output

        elif kind == "in_expr":
            field, items, negate = params
            evaluated = self._get_value(field)
            result = (evaluated not in items) if negate else (evaluated in items)
            return result, self._colorize(
                f"{field}{' not ' if negate else ' '}in {items}", result
            )

        elif kind == "is_defined":
            field, negate = params
            result = (
                (self._get_value(field) is None)
                if negate
                else (self._get_value(field) is not None)
            )
            return result, self._colorize(
                f"{field} is{" not " if negate else " "}defined", result
            )

        elif kind in ("and", "or"):
            left, left_output = self._evaluate_with_debug_output(
                params[0], depth + 1
            )
            right, right_output = self._evaluate_with_debug_output(
                params[1], depth + 1
            )

            if len(left_output) + len(right_output) > 80:
                left_output = f"\n{'  ' * depth}" + left_output
                right_output += f"\n{'  ' * (depth-1)}"
            if kind == "and":
                result = left and right
                return (
                    result,
                    f"({left_output} {self._colorize("AND", result)} {right_output})",
                )
            else:
                result = left or right
                return (
                    result,
                    f"({left_output} {self._colorize("OR", result)} {right_output})",
                )

        elif kind == "func":
            name, args = params
            if name in ("lineItemCount", "lineItemExists"):
                if not args:
                    print(f"Function {name} called with no arguments, returning 0")
                    return 0
                filter_expr = args[0]
                result, debug_output = self._evaluate_with_debug_output(
                    filter_expr, depth + 1
                )

                x = 1 if result else 0

                if debug_output.startswith("(") and debug_output.endswith(")"):
                    debug_output = debug_output[1:-1]

                return x, f"{name}({debug_output}) -> {1 if result else 0}"
            return 0, f"Function {name} not implemented, returning 0"

        return False, f"Unknown expr {expression}"
