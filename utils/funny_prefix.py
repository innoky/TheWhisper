import random

def funny_prefix():
    adj_list = open("adj_list.txt", "r", encoding="utf-8").read().splitlines()
    obj_list = open("obj_list.txt", "r", encoding="utf-8").read().splitlines()
    adj = random.choice(adj_list)
    obj = random.choice(obj_list)
    result = adj + " " + obj + " пришёл и оставил комментарий:"
    return result 