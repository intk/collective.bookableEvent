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
from plone.app.contenttypes.interfaces import IEvent
from plone.app.textfield.value import RichTextValue

import datetime

import plone.api


BUTTON_TEMPLATE = '<p style="text-align: center; "><a class="btn btn-inverse btn-large internal-link" href="resolveuid/%s" target="_self" title="">Reserveer</a></p>'

# # # # # # # # # # # # # # #
# # # # # # # # # # # # # # #
# BookableEvent schema      #
# # # # # # # # # # # # # # #
# # # # # # # # # # # # # # #

class IBookableEvent(form.Schema):
    form.model("models/bookableEvent.xml")

# # # # # # # # # # # # # # # #
# BookableEvent declaration   #
# # # # # # # # # # # # # # # #

class BookableEvent(Container):
    grok.implements(IBookableEvent)

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




def modifiedLimit(obj, event):
    form_id = getattr(obj, 'id', '')
    if form_id == "limit_subscriptions":
        limit = obj.getMaxval()
        obj.setDescription("Er zijn nog %s plaatsen beschikbaar" %(limit))
        obj.setPlaceholder(limit)
        obj.setMinval("0")
    else:
        pass

def createdEvent(obj, event):
    FORM_ID = "opgaveformulier"
    FORM_ID_TEMP = "opgaveformulier-1"
    NEW_LIMIT = "15"
    FORM_ELEM_ID = "limit_subscriptions"
    TEMPLATE_ID = "workshop-template"

    catalog = getToolByName(obj, 'portal_catalog')
    # get form
    forms = catalog(Subject=TEMPLATE_ID, portal_type="FormFolder")
    if forms:
        form = forms[0]
        formFolder = form.getObject()
        target = obj
        source = formFolder

        limit_set = getattr(obj, 'limit_subscriptions', '')
        if limit_set:
            NEW_LIMIT = limit_set

        if FORM_ID_TEMP in obj:
            FORM_ID = FORM_ID_TEMP

        if FORM_ID not in obj:
            plone.api.content.copy(source=source, target=target, safe_id=True)
            if FORM_ID in obj:
                new_form = obj[FORM_ID]
                form_uid = new_form.UID()
                plone.api.content.transition(obj=new_form, transition='publish')

                button = BUTTON_TEMPLATE % (form_uid)

                current_text = getattr(obj, 'text', '')
                if not current_text:
                    new_text = RichTextValue(button, 'text/html', 'text/html')
                    setattr(obj, 'text', new_text)
                else:
                    current_text_raw = current_text.raw
                    new_text_raw = current_text_raw + button
                    new_text = RichTextValue(new_text_raw, 'text/html', 'text/html')
                    setattr(obj, 'text', new_text)

                # Set help veld
                if FORM_ELEM_ID in new_form:
                    limit = new_form['limit_subscriptions']
                    limit.setDescription("Er zijn nog %s plaatsen beschikbaar" %(NEW_LIMIT))
                    limit.setPlaceholder(NEW_LIMIT)
                    limit.setMaxval(NEW_LIMIT)
                    limit.setMinval("0")
                else:
                    # There's no limitation in this form
                    pass

            else:
                # Something went wrong - form was not created
                pass
        else:
            print "Already exists"
            # Edit current form
            new_form = obj[FORM_ID]
            plone.api.content.transition(obj=new_form, transition='publish')
            NEW_ID = "%s" %(FORM_ID)
            
            if FORM_ID_TEMP in obj:
                FORM_ID = "opgaveformulier"
            
            plone.api.content.rename(obj=new_form, new_id=NEW_ID, safe_id=True)
            
            new_form.reindexObject()
            form_uid = new_form.UID()
            button = BUTTON_TEMPLATE % (form_uid)
            
            new_text = RichTextValue(button, 'text/html', 'text/html')
            setattr(obj, 'text', new_text)

            if FORM_ELEM_ID in new_form:
                #limit = new_form['limit_subscriptions']
                #limit.setDescription("Er zijn nog %s plaatsen beschikbaar" %(NEW_LIMIT))
                #limit.setPlaceholder(NEW_LIMIT)
                #limit.setMaxval(NEW_LIMIT)
                #limit.setMinval("0")
                pass
            else:
                # There's no limitation in this form
                pass
    else:
        # Something went wrong. - template was not found
        pass
