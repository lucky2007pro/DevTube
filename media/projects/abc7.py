# def alpha(*args):
#     summa = 1
#     for i in args:
#         if i == 0:
#             pass
#         else:
#             summa *= i
#     return summa
# print(alpha(*[int(i) for i in input("Sonlaringiz: ").split(" ")]))

#1-holat
# def func(a, *args):
#     for i in args[0: -1]:
#         print(a * i, end=" ")
#     print("\n")
#     lst = []
#     for i in args[0: -1]:
#         lst.append(args[-1] / i)
#     print(lst)
# func(*[int(i) for i in input("Sonlaringiz: ").split(" ")])

#2-holat
# def func(a, b, *args):
#     for i in args:
#         print(a * i, end=" ")
#     print("\n")
#     lst = []
#     for i in args:
#         lst.append(b / i)
#     print(lst)
# func(*[int(i) for i in input("Sonlaringiz: ").split(" ")])

# def calc(op, *numbers.txt):
#     if op == '+':
#         return sum(numbers.txt)
#     elif op == '*':
#         s = 1
#         for i in numbers.txt:
#             s *= i
#         return s
#     elif op == '-':
#         i = numbers.txt[0]
#         for j in numbers.txt[1:]:
#             i -= j
#         print(i)
# calc("+", 4, 6 , 56, 4)