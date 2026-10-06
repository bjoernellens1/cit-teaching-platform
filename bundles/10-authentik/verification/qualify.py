"""Run inside `ak shell` in a rollback-only transaction; no mail or human login."""
import json,uuid
from datetime import timedelta
from types import SimpleNamespace
from django.db import transaction
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.core import signing
from django.utils.timezone import now
from authentik.blueprints.v1.importer import Importer
from authentik.core.models import User
from authentik.flows.models import Flow, FlowToken, FlowStageBinding
from authentik.flows.planner import FlowPlanner,FlowNonApplicableException
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.expression.evaluator import PolicyEvaluator
from authentik.policies.types import PolicyRequest
from authentik.stages.email.stage import PLAN_CONTEXT_IS_RESTORED, pickle_flow_token_for_email, EmailStageView
from authentik.stages.email.models import EmailStage
from authentik.stages.consent.stage import ConsentStageView
from unittest.mock import patch
NativeConsent = pickle_flow_token_for_email.__globals__["EmailTokenRevocationConsentStageView"]
assert PLAN_CONTEXT_IS_RESTORED == 'is_restored'
results=[]
with transaction.atomic():
    before=list(FlowStageBinding.objects.exclude(target__slug='cps-email-verification').values_list('pk','stage_id','order'))
    importer=Importer.from_string(BLUEPRINT)
    assert importer.apply(), 'Native blueprint import failed'
    flow=Flow.objects.get(slug='cps-email-verification')
    assert flow.authentication=='require_authenticated' and flow.designation=='stage_configuration'
    assert list(FlowStageBinding.objects.exclude(target=flow).values_list('pk','stage_id','order'))==before
    u=User.objects.create(username='qualification-email-'+uuid.uuid4().hex,email='fixture@example.invalid',attributes={})
    other=User.objects.create(username='qualification-email-'+uuid.uuid4().hex,email='other@example.invalid',attributes={})
    expression=ExpressionPolicy.objects.get(name='cps-email-verification-record').expression
    def evaluate(expr,user,context):
        http=RequestFactory().get('/');http.user=user
        req=PolicyRequest(user);req.http_request=http;req.context={'flow_plan':SimpleNamespace(context=context)}
        e=PolicyEvaluator('verification-qualification');e.set_policy_request(req)
        return e.evaluate(expr).passing
    def token(user=u,expired=False,token_flow=flow,consumed=True):
        t=FlowToken.objects.create(identifier='ak-email-stage-cps-email-verification-email-'+uuid.uuid4().hex,user=user,flow=token_flow,expires=now()+timedelta(minutes=-1 if expired else 15),_plan=b'')
        if consumed:
            view=NativeConsent(SimpleNamespace(plan=SimpleNamespace(context={'is_restored':t})))
            with patch.object(ConsentStageView, 'challenge_valid', return_value=None):view.challenge_valid(SimpleNamespace())
            assert t.pk is None
        return t
    def context(t):return {'is_restored':t,'cps_verification_user':str(u.pk),'cps_verification_email':u.email}
    for name,user,ctx in [('anonymous',AnonymousUser(),context(token())),('missing-token',u,{}),('unconfirmed-link',u,context(token(consumed=False))),('expired',u,context(token(expired=True))),('wrong-user',u,context(token(user=other))),('missing-user-snapshot',u,{'is_restored':token(),'cps_verification_email':u.email}),('changed-email',u,{**context(token()),'cps_verification_email':'previous@example.invalid'})]:
        assert evaluate(expression,user,ctx) is True,name
        u.refresh_from_db();assert 'cps/email-verification' not in u.attributes,name
        results.append(name+' denied without proof')
    wrong=Flow.objects.create(name='fixture',slug='qualification-'+uuid.uuid4().hex,title='fixture',designation='stage_configuration')
    assert evaluate(expression,u,context(token(token_flow=wrong))) is True
    results.append('wrong-flow denied')
    t=token();ctx=context(t)
    assert evaluate(expression,u,ctx) is False
    u.refresh_from_db();signed=u.attributes['cps/email-verification']
    proof=signing.loads(signed,salt='cps.email-verification.v1')
    assert proof['user_id']==str(u.pk) and proof['email']==u.email and proof['verified_at']
    assert t.pk is None
    assert evaluate(expression,u,ctx) is True
    results.extend(['valid token records signed exact-address proof','token consumed and replay denied'])
    try:signing.loads(signed+'tamper',salt='cps.email-verification.v1');raise AssertionError('Tampered proof accepted')
    except signing.BadSignature:pass
    assert proof['user_id']!=str(other.pk)
    u.email='changed@example.invalid';u.save(update_fields=['email']);assert proof['email']!=u.email
    results.extend(['tampered/copied/changed-address proof cannot qualify current identity','existing flow bindings unchanged'])
    prep=ExpressionPolicy.objects.get(name='cps-email-verification-prepare').expression
    FlowToken.objects.filter(identifier='cps-email-verification-cooldown-'+str(u.pk)).delete()
    try:
        pc={};assert evaluate(prep,u,pc) is False;assert pc['pending_user']==u and pc['email']==u.email
        http=RequestFactory().get('/');http.user=u
        native_plan=FlowPlanner(flow).plan(http);native_plan.context=pc
        native_view=EmailStageView(SimpleNamespace(flow=flow,current_stage=EmailStage.objects.get(name='cps-email-verification-email'),plan=native_plan))
        native_token=native_view.get_token()
        restored=native_token.plan
        assert restored.context['cps_verification_email']==u.email and restored.context['cps_verification_user']==str(u.pk)
        assert restored.context['pending_user'].pk==u.pk
        results.append('native email-token serialization preserves exact-address and user snapshot')
        assert evaluate(prep,u,{}) is True
        assert evaluate(prep,AnonymousUser(),{}) is True
        results.append('initial-send throttle and anonymous denial')
    finally:FlowToken.objects.filter(identifier='cps-email-verification-cooldown-'+str(u.pk)).delete()
    http=RequestFactory().get('/');http.user=AnonymousUser()
    try:FlowPlanner(flow).plan(http);raise AssertionError('Anonymous flow planned')
    except FlowNonApplicableException:pass
    results.append('native planner requires authenticated visitor')
    transaction.set_rollback(True)
print('VERIFICATION_QUALIFICATION='+json.dumps({'passed':results,'rollback_only':True,'no_email_sent':True}))
