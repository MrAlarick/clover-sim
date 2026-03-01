import sys

vse_v_kuchu = sys.stdin.read().split()
ukazatel = 0


def chitai_chislo():
    global ukazatel
    res = int(vse_v_kuchu[ukazatel])
    ukazatel += 1
    return res


n = chitai_chislo()
bashni = []
for i in range(n):
    bashni.append(chitai_chislo())

q = chitai_chislo()

for _ in range(q):
    gde = chitai_chislo() - 1
    sila = chitai_chislo()

    schetchik = 0
    shag = gde

    while sila > 0 and shag < n:
        if bashni[shag] >= sila:
            break

        bashni[shag] = 0
        sila -= 1
        shag += 1
        schetchik += 1

    print(schetchik)