import re
import json
import sys

class Token:
    def __init__(self, type, value, position):
        self.type = type
        self.value = value
        self.position = position

class Lexer:
    def __init__(self, text):
        self.text = text
        self.position = 0
        self.tokens = self.tokenize()

    def tokenize(self):
        token_specification = [
            ('COMMENT',  r'#.*'),
            ('FN',       r'fn'),
            ('BOOL', r'true|false'),
            ('ID',       r'[a-zA-Z][a-zA-Z0-9-_]*'),
            ('OP',       r'[&|~()]'),
            ('COMMA',    r','),
            ('WHITESPACE', r'[ \t\n\r]+'),
            ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
        tokens = []
        for mo in re.finditer(tok_regex, self.text):
            kind = mo.lastgroup
            value = mo.group()
            position = mo.start()
            if kind == 'WHITESPACE' or kind == 'COMMENT':
                continue
            elif kind == 'MISMATCH':
                raise RuntimeError(f'Unexpected character at position {position}: {value}')
            tokens.append(Token(kind, value, position))
        tokens.append(Token('EOF', '', len(self.text)))
        return tokens

    def peek(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def consume(self):
        token = self.peek()
        self.position += 1
        return token

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.consume()

    def error(self, expected):
        token = self.current_token
        raise SyntaxError(f"error: expecting '{expected}' but got '{token.value}'\n{self.lexer.text}\n{' ' * token.position}^")

    def consume(self, expected_type):
        if self.current_token.type == expected_type:
            token = self.current_token
            self.current_token = self.lexer.consume()
            return token
        self.error(expected_type)

    def parse_program(self):
        result = []
        while self.current_token.type != 'EOF':
            if self.current_token.type == 'FN':
                result.append(self.parse_definition())
            else:
                result.append(self.parse_expression())
        return result

    def parse_definition(self):
        self.consume('FN')
        name = self.consume('ID').value
        self.consume('OP')  # (
        formals = []
        if self.current_token.type == 'ID':
            formals.append(self.consume('ID').value)
            while self.current_token.type == 'COMMA':
                self.consume('COMMA')
                formals.append(self.consume('ID').value)
        self.consume('OP')  # )
        body = self.parse_expression()
        return {"body": body, "formals": formals, "name": name, "tag": "def"}

    def parse_expression(self):
        left = self.parse_prefix_expression()
        while self.current_token.value in ['&', '|']:
            op = self.consume('OP').value
            right = self.parse_prefix_expression()
            left = {"rand1": left, "rand2": right, "tag": op}
        return left

    def parse_prefix_expression(self):
        if self.current_token.value == '~':
            self.consume('OP')
            operand = self.parse_prefix_expression()
            return {"tag": "~", "rand1": operand}
        return self.parse_primary_expression()

    def parse_primary_expression(self):
        if self.current_token.type == 'BOOL':
            return {"tag": "bool", "value": self.consume('BOOL').value}
        elif self.current_token.type == 'ID':
            id_token = self.consume('ID')
            if self.current_token.value == '(':
                return self.parse_function_application(id_token.value)
            return {"name": id_token.value, "tag": "id"}
        elif self.current_token.value == '(':
            self.consume('OP')
            expr = self.parse_expression()
            self.consume('OP')  # )
            return expr
        self.error('primary expression')

    def parse_function_application(self, name):
        self.consume('OP')  # (
        args = []
        if self.current_token.value != ')':
            args.append(self.parse_expression())
            while self.current_token.type == 'COMMA':
                self.consume('COMMA')
                args.append(self.parse_expression())
        self.consume('OP')  # )
        return {"args": args, "name": name, "tag": "app"}

def main():
    try:
        text = sys.stdin.read()
        lexer = Lexer(text)
        parser = Parser(lexer)
        result = parser.parse_program()
        print(json.dumps(result))
    except (RuntimeError, SyntaxError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
