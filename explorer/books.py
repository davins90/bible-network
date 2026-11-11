# (osis, nome inglese ESV/NLT, nome italiano, abbreviazione italiana)
BOOKS = [
("Gen","Genesis","Genesi","Gn"),("Exod","Exodus","Esodo","Es"),("Lev","Leviticus","Levitico","Lv"),("Num","Numbers","Numeri","Nm"),("Deut","Deuteronomy","Deuteronomio","Dt"),
("Josh","Joshua","Giosuè","Gs"),("Judg","Judges","Giudici","Gdc"),("Ruth","Ruth","Rut","Rt"),("1Sam","1 Samuel","1 Samuele","1Sam"),("2Sam","2 Samuel","2 Samuele","2Sam"),
("1Kgs","1 Kings","1 Re","1Re"),("2Kgs","2 Kings","2 Re","2Re"),("1Chr","1 Chronicles","1 Cronache","1Cr"),("2Chr","2 Chronicles","2 Cronache","2Cr"),("Ezra","Ezra","Esdra","Esd"),
("Neh","Nehemiah","Neemia","Ne"),("Esth","Esther","Ester","Est"),("Job","Job","Giobbe","Gb"),("Ps","Psalm","Salmi","Sal"),("Prov","Proverbs","Proverbi","Pr"),
("Eccl","Ecclesiastes","Ecclesiaste","Ec"),("Song","Song of Solomon","Cantico dei Cantici","Ct"),("Isa","Isaiah","Isaia","Is"),("Jer","Jeremiah","Geremia","Ger"),("Lam","Lamentations","Lamentazioni","Lam"),
("Ezek","Ezekiel","Ezechiele","Ez"),("Dan","Daniel","Daniele","Dn"),("Hos","Hosea","Osea","Os"),("Joel","Joel","Gioele","Gle"),("Amos","Amos","Amos","Am"),
("Obad","Obadiah","Abdia","Abd"),("Jonah","Jonah","Giona","Gna"),("Mic","Micah","Michea","Mi"),("Nah","Nahum","Naum","Na"),("Hab","Habakkuk","Abacuc","Ab"),
("Zeph","Zephaniah","Sofonia","Sof"),("Hag","Haggai","Aggeo","Ag"),("Zech","Zechariah","Zaccaria","Zc"),("Mal","Malachi","Malachia","Ml"),
("Matt","Matthew","Matteo","Mt"),("Mark","Mark","Marco","Mc"),("Luke","Luke","Luca","Lc"),("John","John","Giovanni","Gv"),("Acts","Acts","Atti","At"),
("Rom","Romans","Romani","Rm"),("1Cor","1 Corinthians","1 Corinzi","1Co"),("2Cor","2 Corinthians","2 Corinzi","2Co"),("Gal","Galatians","Galati","Gal"),("Eph","Ephesians","Efesini","Ef"),
("Phil","Philippians","Filippesi","Fil"),("Col","Colossians","Colossesi","Col"),("1Thess","1 Thessalonians","1 Tessalonicesi","1Ts"),("2Thess","2 Thessalonians","2 Tessalonicesi","2Ts"),("1Tim","1 Timothy","1 Timoteo","1Tm"),
("2Tim","2 Timothy","2 Timoteo","2Tm"),("Titus","Titus","Tito","Tt"),("Phlm","Philemon","Filemone","Fm"),("Heb","Hebrews","Ebrei","Eb"),("Jas","James","Giacomo","Gc"),
("1Pet","1 Peter","1 Pietro","1Pt"),("2Pet","2 Peter","2 Pietro","2Pt"),("1John","1 John","1 Giovanni","1Gv"),("2John","2 John","2 Giovanni","2Gv"),("3John","3 John","3 Giovanni","3Gv"),
("Jude","Jude","Giuda","Gd"),("Rev","Revelation","Apocalisse","Ap"),
]
SINGLE = {"Obad","Phlm","2John","3John","Jude"}
BY_EN = {b[1]: i for i, b in enumerate(BOOKS)}
BY_OSIS = {b[0]: i for i, b in enumerate(BOOKS)}
