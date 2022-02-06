import time, re, html, sys, requests, json, urllib3, urllib.parse
from bs4 import BeautifulSoup as soup

def base_url(url, with_path=False):
    parsed = urllib.parse.urlparse(url)
    path   = '/'.join(parsed.path.split('/')[:-1]) if with_path else ''
    parsed = parsed._replace(path=path)
    parsed = parsed._replace(params='')
    parsed = parsed._replace(query='')
    parsed = parsed._replace(fragment='')
    return parsed.geturl()

	
def product_search_atc(session):
    productFound = False

    while (productFound == False):
        print("Getting Product...")
        productDict = {}
        link = product_url + '.js'
        r = session.get(link, verify=False)
        bs = soup(r.text, "html.parser")
        site_json = json.loads(bs.text)
		
        variantDict = {}

        if not variantDict:
            for _entry in site_json['variants']:
                variantID = _entry['id']
                variantDict.update({_entry['name']: variantID})
        return variantDict
				

def add_to_cart(session):
    variantDict = product_search_atc(session)
    addToCartVariantlist = []

    for key in variantDict:
        addToCartVariantlist.append(str(variantDict.get(key)))

    for addToCartVariant in addToCartVariantlist:
        link = url_base + "/cart/add.js?quantity=5000&id=" + addToCartVariant
        print(f"Adding - {addToCartVariant}")
        response = session.get(link, verify=False)
        addToCartData = json.loads(response.text)
        try:
            checkAddToCart = addToCartData["quantity"]
            if (checkAddToCart < 1):
                print("Not in stock!")
        except KeyError:
            print(Fore.RED + "Attempting Add to Cart")
			
    return response
            
			
def start_checkout(session):
    add_to_cart(session)
    tempLink = url_base + "/checkout.json"
    response = session.get(tempLink, verify=False, allow_redirects=True)
    bs = soup(response.text, "html.parser")
    print("Checking In Stock")
    _stockcheckre = re.findall('product__description__name page-main__emphasis">(.+)<\/span>\s+<span class="product__description__variant page-main__small-text">(.*)<\/span>\s+</th>\s+<td class="product__status product__status--reduced">\s+.+<span class="page-main__emphasis">(\d+)<\/span>', str(bs))
    print("Checking Sold Out")
    _soldoutre = re.findall('product__description__name page-main__emphasis">(.+)<\/span>\s+<span class="product__description__variant page-main__small-text">(.*)<\/span>\s+</th>\s+<td class="product__status product__status--sold-out">', str(bs))
    _returndict = dict()
    for item in _stockcheckre:
        _productname = f"{html.unescape(item[0])} - {html.unescape(item[1])}" if item[1] else html.unescape(item[0])
        _returndict[_productname] = item[2]
    for item in _soldoutre:
        _productname = f"{html.unescape(item[0])} - {html.unescape(item[1])}" if item[1] else html.unescape(item[0])
        _returndict[_productname] = 'Sold Out'
    print(_returndict)


product_url = sys.argv[1]
url_base = base_url(product_url)
session = requests.session()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
start_checkout(session)