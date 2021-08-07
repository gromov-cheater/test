from lxml import etree

class Parser:
    def __init__(self):
        self.parser = etree.XMLParser(remove_comments=True)

    def parse_clothes(self):
        doc = etree.parse("config/inventory/clothes.xml",
                          parser=self.parser)
        root = doc.getroot()
        clths = {'boy': {}, 'girl': {}}
        for element in root.find('category'):
            if element.attrib['gender'] in clths:
                gender = element.attrib['gender']
                for el in element.findall('category'):
                    for c in el.findall('item'):
                        clths[gender][c.attrib['id']] = {}
                        for item in c.attrib:
                            clths[gender][c.attrib['id']][item] = c.attrib[item]
                    for els in el.findall('category'):
                        for cc in els.findall('item'):
                            clths[gender][cc.attrib['id']] = {}
                            for item in cc.attrib:
                                clths[gender][cc.attrib['id']][item] = cc.attrib[item]
                        for elss in els.findall('category'):
                            for ccc in elss.findall('item'):
                                clths[gender][ccc.attrib['id']] = {}
                                for item in ccc.attrib:
                                    clths[gender][ccc.attrib['id']][item] = ccc.attrib[item]
                            for elsss in elss.findall('category'):
                                for cccc in elsss.findall('item'):
                                    clths[gender][cccc.attrib['id']] = {}
                                    for item in cccc.attrib:
                                        clths[gender][cccc.attrib['id']][item] = cccc.attrib[item]
                                for elssss in elsss.findall('category'):
                                    for ccccc in elssss.findall('item'):
                                        clths[gender][ccccc.attrib['id']] = {}
                                        for item in ccccc.attrib:
                                            clths[gender][ccccc.attrib['id']][item] = ccccc.attrib[item]
        return clths

    def parse_furniture(self):
        furniture = {}
        for filename in ["furniture.xml", "kitchen.xml", "bathroom.xml",
                         "decor.xml", "present.xml", "roomLayout.xml"]:
            doc = etree.parse(f"config/inventory/{filename}",
                              parser=self.parser)
            root = doc.getroot()
            for item in root.findall(".//item"):
                name = item.attrib["id"]
                furniture[name] = {}
                for attr in ["gold", "rating", "silver", 'canBuy']:
                    if attr in item.attrib:
                        furniture[name][attr] = int(item.attrib[attr])
                    else:
                        if attr == "canBuy":
                            value = 1
                        else:
                            value = 0
                        furniture[name][attr] = value
                furniture[name]['slot'] = filename.split('.')[0]
        return furniture

    def parse_craft(self):
        doc = etree.parse("config/modules/craft.xml",
                          parser=self.parser)
        root = doc.getroot()
        items = {}
        for item in root.findall(".//craftedItem"):
            views = None
            id_ = item.attrib["itemId"]
            if 'views' in item.attrib:
                views = item.attrib['views']
            items[id_] = {"items": {}, 'views': views}
            if "craftedId" in item.attrib:
                items[id_]["craftedId"] = item.attrib["craftedId"]
                items[id_]["count"] = int(item.attrib["count"])
            for tmp in item.findall("component"):
                itemId = tmp.attrib["itemId"]
                count = int(tmp.attrib["count"])
                items[id_]["items"][itemId] = count
        return items

    def parse_game_items(self):
        doc = etree.parse("config/inventory/game.xml",
                          parser=self.parser)
        root = doc.getroot()
        items = {}
        for category in root.findall(".//category"):
            cat_name = category.attrib["id"]
            items[cat_name] = {}
            for item in category.findall(".//item"):
                name = item.attrib["id"]
                items[cat_name][name] = {}
                for attr in ["gold", "silver", "saleSilver"]:
                    if attr in item.attrib:
                        items[cat_name][name][attr] = int(item.attrib[attr])
                    else:
                        if attr == "saleSilver":
                            continue
                        items[cat_name][name][attr] = 0
                for attr in ["canBuy"]:
                    if attr in item.attrib:
                        items[cat_name][name][attr] = bool(int(item.attrib[attr]))
                    else:
                        if attr == "canBuy":
                            items[cat_name][name][attr] = True
                        else:
                            items[cat_name][name][attr] = False
        return items
