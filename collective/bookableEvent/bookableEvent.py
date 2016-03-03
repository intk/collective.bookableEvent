#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Zope dependencies
#
from five import grok

from z3c.form import group, field
from zope import schema
from zope.interface import invariant, Invalid
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone.dexterity.content import Container
from zope.component import getMultiAdapter

from plone.directives import dexterity, form
from plone.app.textfield import RichText
from plone.namedfile.field import NamedImage, NamedFile
from plone.namedfile.field import NamedBlobImage, NamedBlobFile
from plone.namedfile.interfaces import IImageScaleTraversable
from plone.dexterity.browser.view import DefaultView

from Products.mediaObject import MessageFactory as _
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.PloneBatch import Batch
from Products.CMFCore.utils import getToolByName
from collective.leadmedia.interfaces import ICanContainMedia
from zope.schema import getFieldsInOrder
from collective import dexteritytextindexer
from zope.component import adapts
from zope.interface import implements

import datetime


# # # # # # # # # # # # # # #
# # # # # # # # # # # # # # #
# BookableEvent schema      #
# # # # # # # # # # # # # # #
# # # # # # # # # # # # # # #



class IBookableEvent(form.Schema):
    text = RichText(
        title=_(u"Body"),
        required=False
    )

# # # # # # # # # # # # # # # #
# BookableEvent declaration   #
# # # # # # # # # # # # # # # #

class BookableEvent(Container):
    grok.implements(IBookableEvent)
    pass

class BookableEventView(DefaultView):
    def getFBdetails(self):
        item = self.context
        
        state = getMultiAdapter(
                (item, self.request),
                name=u'plone_context_state')

        # Check view type
        view_type = state.view_template_id()

        obj = ICanContainMedia(item)

        details = {}
        details["title"] = item.Title()
        details["type"] = "article"
        details["site_name"] = "Teylers Museum"
        details["url"] = item.absolute_url()
        details["description"] = item.Description()
        details["double_image"] = ""
        details["image"] = ""
        
        if view_type == "instruments_view":
            if hasattr(item, 'slideshow'):
                catalog = getToolByName(self.context, 'portal_catalog')
                slideshow = item['slideshow']
                path = '/'.join(slideshow.getPhysicalPath())
                results = catalog.searchResults(path={'query': path, 'depth': 1, 'portal_type': 'Image'}, sort_on='sortable_title')
                if len(results) > 0:
                    lead_image = results[0]
                    if lead_image.portal_type == "Image":
                        details["image"] = lead_image.getObject().absolute_url()+"/@@images/image/large"
                else:
                    details["image"] = ""
                

        if details["image"] == "":
            if obj.hasMedia():
                image = obj.getLeadMedia()
                details["image"] = image.absolute_url()+"/@@images/image/large"
                
                if view_type == "double_view":
                    if hasattr(item, 'slideshow'):
                        slideshow = item['slideshow']
                        if len(slideshow.objectIds()) > 1:
                            double_image = slideshow[slideshow.objectIds()[1]]
                            if double_image.portal_type == "Image":
                                details["double_image"] = double_image.absolute_url()+"/@@images/image/large"
            else:
                details["image"] = ""

        return details


