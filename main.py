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

	
def product_search_atc(session, _url):
  try:
  	print("Getting Product...")
  	productDict = {}
  	link = _url + '.js'
  	r = session.get(link, verify=False)
  	bs = soup(r.text, "html.parser")
  	site_json = json.loads(bs.text)
  	
  	variantDict = {}
  	stockDict = {}
  
  	if not variantDict:
  		for _entry in site_json['variants']:
  			variantID = _entry['id']
  			if 'name' in _entry:
  			  _prodName = _entry['name']
  			else:
  			  _prodName = site_json['title']
  			variantDict.update({_prodName: variantID})
  			if 'inventory_quantity' in _entry:
  			  stockDict.update({_prodName: _entry['inventory_quantity']})
  	return variantDict, stockDict, site_json['title']
  except Exception as e:
    print(e)
    return variantDict, stockDict, site_json['title']	

def add_to_cart(session, url_base, _url):
    variantDict, stockDict, prodTitle = product_search_atc(session, _url)
    if not stockDict:
      addToCartVariantlist = []
  
      for key in variantDict:
          addToCartVariantlist.append(str(variantDict.get(key)))
  
      for addToCartVariant in addToCartVariantlist:
          link = url_base + "/cart/add.js?quantity=15000&id=" + addToCartVariant
          print(f"Adding - {addToCartVariant}")
          response = session.get(link, verify=False)	
    return stockDict, prodTitle
            
			
def shopify_check(session, url_base, _url):
    print("ADDING TO CART")
    _addtocartResult, _prodTitle = add_to_cart(session, url_base, _url)
    _returndict = dict()
    if not _addtocartResult:
      tempLink = url_base + "/checkout.json"
      response = session.get(tempLink, verify=False, allow_redirects=True)
      bs = soup(response.text, "html.parser")
      print("Checking In Stock")
      _stockcheckre = re.findall('product__description__name page-main__emphasis">(.+)<\/span>\s+<span class="product__description__variant page-main__small-text">(.*)<\/span>\s+</th>\s+<td class="product__status product__status--reduced">\s+.+<span class="page-main__emphasis">(\d+)<\/span>', str(bs))
      print("Checking Sold Out")
      _soldoutre = re.findall('product__description__name page-main__emphasis">(.+)<\/span>\s+<span class="product__description__variant page-main__small-text">(.*)<\/span>\s+</th>\s+<td class="product__status product__status--sold-out">', str(bs))
      for item in _stockcheckre:
          _productname = f"{html.unescape(item[0])} - {html.unescape(item[1])}" if item[1] else html.unescape(item[0])
          _returndict[_productname] = item[2]
      for item in _soldoutre:
          _productname = f"{html.unescape(item[0])} - {html.unescape(item[1])}" if item[1] else html.unescape(item[0])
          _returndict[_productname] = 'Sold Out'
      if not _soldoutre and not _stockcheckre:
        print("Checking graphsql")
        _productList = []
        _stocklist = []
        try:
          site_json = json.loads(html.unescape(bs.find("div", {"data-serialized-id":"graphql"})['data-serialized-value']))
          for _element in site_json:
              if 'session' in site_json[_element]:
                  _rawproductList = site_json[_element]['session']['negotiate']['result']['buyerProposal']['merchandise']['merchandiseLines']
                  for _product in _rawproductList:
                      _productname = f"{_product['merchandise']['title']} - {_product['merchandise']['subtitle']}" if _product['merchandise']['subtitle'] else _product['merchandise']['title']
                      _productList.append(_productname)
                  _rawerrorlist = site_json[_element]['session']['negotiate']['errors']
                  for _error in _rawerrorlist:
                      if _error['code'] == 'MERCHANDISE_NOT_ENOUGH_STOCK_AVAILABLE':
                          _stockcount = int(re.findall(r'(\d+)', _error['localizedMessage'])[0])
                          _stocklist.append(_stockcount)
                      elif _error['code'] == 'MERCHANDISE_OUT_OF_STOCK':
                          _stocklist.append('Sold Out')
          _returndict = dict(zip(_productList, _stocklist))
        except Exception as e:
          print(e)
        if not _returndict:
            _returndict['message'] = 'No quantity limit found'
    else:
      for item in _addtocartResult:
          _productname = item
          if _addtocartResult[item] < 1:
              _returndict[_productname] = 'Sold Out'
          else:
              _returndict[_productname] = _addtocartResult[item]
    return _returndict


def bandcamp_check(session, product_url):
    response = session.get(product_url, verify=False, allow_redirects=True)
    bs = soup(response.text, "html.parser")
    #_element = bs.find('script', {"type":"application/ld+json"}) 
    try:
      _titleTrack = bs.find('h2', {"class":"trackTitle"})
      _prodTitle = _titleTrack.string.strip()
    except:
      _merchTitle = bs.find('h2', {"class":"title"})
      _prodTitle = _merchTitle.string.strip() if _merchTitle else product_url
    try:
      _returndict = dict()
      #if _element:
      #  _jsonElem = json.loads(_element.string)['albumRelease']
      #  for _item in _jsonElem:
      #      try:
      #          _productname = _item['name']
      #          if _item['offers']:
      #              if _item['offers']['availability'] != 'InStock' and _item['offers']['availability'] != 'OnlineOnly':
      #                  _returndict[_productname] = 'Sold Out'
      #              else:
      #                  for _property in _item['offers']['additionalProperty']:
      #                      if _property['name'] == 'quantity_available':	
      #                          _returndict[_productname] = _property['value']
      #      except:
      #          pass
      if _returndict:
          return _returndict
      else:
          _element = bs.find('script', {"type":"text/javascript", "data-tralbum": True})['data-tralbum']
          _jsonElem = json.loads(html.unescape(_element))['packages']
          try:
            for _entry in _jsonElem:
              if 'quantity_available' in _entry:
                _productname = _entry['title']
                _returndict[_productname] = _entry['quantity_available'] if _entry['quantity_available'] != 0 else 'Sold Out'
          except:
            pass
          if _returndict:
            return _returndict
          else:
            return {'message': f'Item info not available'}
    except Exception as e:
        print(e)
        return {'message': f'Item info not available'}

	
def checkStock(_url):
    url_base = base_url(_url)
    session = requests.session()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if 'bandcamp' in _url:
        return bandcamp_check(session, _url)
    else:
        return shopify_check(session, url_base, _url)


try:
	input_url = sys.argv[1].split('?')[0]
except:
	input_url = sys.argv[1]

print(f"Checking stock for {input_url}")
print(checkStock(input_url))