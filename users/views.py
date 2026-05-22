# users/views.py
import os
import re
import requests as http_requests
from .models import SiteSettings

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.conf import settings
from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CustomUserSerializer,
    UserLoginSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer,
)

CustomUser = get_user_model()

# ── Disposable email blocklist ─────────────────────────────────────────────────
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "guerrillamail.info", "guerrillamail.biz",
    "guerrillamail.de", "guerrillamail.net", "guerrillamail.org", "guerrillamailblock.com",
    "grr.la", "sharklasers.com", "spam4.me", "tempmail.com", "tempmail.net",
    "tempr.email", "tempomail.fr", "temp-mail.org", "temp-mail.io", "throwam.com",
    "trashmail.com", "trashmail.at", "trashmail.io", "trashmail.me", "trashmail.xyz",
    "yopmail.com", "yopmail.fr", "cool.fr.nf", "jetable.fr.nf", "nospam.ze.tc",
    "nomail.xl.cx", "mega.zik.dj", "speed.1s.fr", "courriel.fr.nf", "moncourrier.fr.nf",
    "monemail.fr.nf", "monmail.fr.nf", "maildrop.cc", "dispostable.com", "mailnull.com",
    "spamgourmet.com", "fakeinbox.com", "getairmail.com", "filzmail.com",
    "discard.email", "spamfree24.org", "mailexpire.com", "spamspot.com",
    "mt2015.com", "objectmail.com", "obobbo.com", "rtrtr.com", "safetymail.info",
    "tempinbox.com", "thanksnospam.info", "trbvm.com", "wegwerfmail.de",
    "wegwerfmail.net", "wegwerfmail.org", "throwam.com", "mailnesia.com",
    "mailnull.com", "spamgourmet.net", "spamgourmet.org", "binkmail.com",
    "bobmail.info", "chammy.info", "devnullmail.com", "discard.email",
    "discardmail.com", "discardmail.de", "disposableaddress.com",
    "disposableemailaddresses.com", "disposeamail.com", "disposemail.com",
    "dodgit.com", "dumpandfuck.com", "e4ward.com", "emailias.com",
    "emailinfive.com", "emailsensei.com", "emailtemporario.com.br",
    "emailthe.net", "emailto.de", "emailwarden.com", "emz.net",
    "fakedemail.com", "fakeinformation.com", "fastacura.com", "fastchevy.com",
    "fastchrysler.com", "fastkawasaki.com", "fastmazda.com", "fastmitsubishi.com",
    "fastnissan.com", "fastsubaru.com", "fastsuzuki.com", "fasttoyota.com",
    "fastyamaha.com", "fivemail.de", "fleckens.hu", "frapmail.com",
    "gowikibooks.com", "gowikicampus.com", "gowikicars.com", "gowikifilms.com",
    "gowikigames.com", "gowikimail.com", "gowikimusic.com", "gowikinetwork.com",
    "gowikitravel.com", "gowikitv.com", "hatespam.org", "herp.in",
    "hidemail.de", "hochsitze.com", "hushmail.com", "ieatspam.eu",
    "ieatspam.info", "inboxclean.com", "inboxclean.org", "jetable.com",
    "jetable.fr.nf", "jetable.net", "jetable.org", "junk1.tk",
    "kasmail.com", "kaspop.com", "killmail.com", "killmail.net",
    "klassmaster.com", "klzlk.com", "koszmail.pl", "kurzepost.de",
    "letthemeatspam.com", "lhsdv.com", "lifebyfood.com", "link2mail.net",
    "litedrop.com", "lol.ovpn.to", "lolfreak.net", "lookugly.com",
    "lortemail.dk", "lr78.com", "lroid.com", "lukop.dk",
    "m21.cc", "mail-filter.com", "mail-temporaire.fr", "mail.by",
    "mail2rss.org", "mail333.com", "mailblocks.com", "mailbucket.org",
    "mailcat.biz", "mailcatch.com", "maileater.com", "maileme101.com",
    "mailforspam.com", "mailfreeonline.com", "mailguard.me", "mailin8r.com",
    "mailinatar.com", "mailme.ir", "mailme.lv", "mailme24.com",
    "mailmetrash.com", "mailmoat.com", "mailnew.com", "mailnull.net",
    "mailpick.biz", "mailrock.biz", "mailscrap.com", "mailshell.com",
    "mailsiphon.com", "mailslite.com", "mailtemp.info", "mailtome.de",
    "mailtothis.com", "mailzilla.com", "mailzilla.org", "makemetheking.com",
    "mbx.cc", "mega.zik.dj", "meinspamschutz.de", "meltmail.com",
    "messagebeamer.de", "mezimages.net", "ministry-of-silly-walks.de",
    "mireille.name", "mjukglass.nu", "moakt.com", "mobi.web.id",
    "mobileninja.co.uk", "moburl.com", "moncourrier.fr.nf", "monemail.fr.nf",
    "monmail.fr.nf", "msa.minsmail.com", "mt2009.com", "mx0.wwwnew.eu",
    "my10minutemail.com", "mycard.net.ua", "mycleaninbox.net", "mymail-in.net",
    "mypacks.net", "mypartyclip.de", "myphantomemail.com", "myspaceinc.com",
    "myspaceinc.net", "myspaceinc.org", "myspacepimpedup.com", "myspamless.com",
    "mytempemail.com", "mytempmail.com", "mytrashmail.com", "nabuma.com",
    "neomailbox.com", "nepwk.com", "nervmich.net", "nervtmich.net",
    "netmails.com", "netmails.net", "netzidiot.de", "nevermail.de",
    "no-spam.ws", "noblepioneer.com", "nobulk.com", "noclickemail.com",
    "nogmailspam.info", "nomail.pw", "nomail.xl.cx", "nomail2me.com",
    "nomorespamemails.com", "nonspam.eu", "nonspammer.de", "noref.in",
    "nospam.ze.tc", "nospam4.us", "nospamfor.us", "nospammail.net",
    "nospamthanks.info", "notmailinator.com", "notsharingmy.info",
    "nowhere.org", "nowmymail.com", "nwldx.com", "objectmail.com",
    "obobbo.com", "odaymail.com", "oneoffemail.com", "oneoffmail.com",
    "onewaymail.com", "onlatedotcom.info", "online.ms", "oopi.org",
    "opayq.com", "ordinaryamerican.net", "otherinbox.codupmyspace.com",
    "otherinbox.com", "ovpn.to", "owlpic.com", "pancakemail.com",
    "pimpedupmyspace.com", "pjjkp.com", "plexolan.de", "poczta.onet.pl",
    "politikerclub.de", "poofy.org", "pookmail.com", "privacy.net",
    "privatdemail.net", "proxymail.eu", "prtnx.com", "prtz.eu",
    "pubmail.io", "putthisinyourspamdatabase.com", "putthisinyourspamdatabase.com",
    "qq.com", "quickinbox.com", "rcpt.at", "reallymymail.com",
    "recursor.net", "recyclemail.dk", "regbypass.com", "regbypass.comsafe-mail.net",
    "rhyta.com", "rklips.com", "rmqkr.net", "royal.net",
    "rppkn.com", "rtrtr.com", "s0ny.net", "safe-mail.net",
    "safetymail.info", "safetypost.de", "sandelf.de", "schafmail.de",
    "schrott-email.de", "secretemail.de", "secure-mail.biz", "selfdestructingmail.com",
    "sendspamhere.com", "sevgithb.com", "shadowmail.info", "sharedmailbox.org",
    "shiftmail.com", "shhmail.com", "shitmail.de", "shitmail.me",
    "shitmail.org", "shitware.nl", "shortmail.net", "sibmail.com",
    "skeefmail.com", "slapsfromlastnight.com", "slaskpost.se", "slave-auctions.net",
    "slopsbox.com", "slowslow.de", "smellfear.com", "smwg.info",
    "snipermail.info", "snkmail.com", "sofimail.com", "sofort-mail.de",
    "sogetthis.com", "soodonims.com", "spam.la", "spam.org.tr",
    "spam.su", "spam4.me", "spamavert.com", "spambob.com",
    "spambob.net", "spambob.org", "spambog.com", "spambog.de",
    "spambog.ru", "spambox.info", "spambox.irishspringrealty.com", "spambox.us",
    "spamcannon.com", "spamcannon.net", "spamcero.com", "spamcon.org",
    "spamcorptastic.com", "spamcowboy.com", "spamcowboy.net", "spamcowboy.org",
    "spamday.com", "spamex.com", "spamfree.eu", "spamfree24.de",
    "spamfree24.eu", "spamfree24.info", "spamfree24.net", "spamfree24.org",
    "spamgoes.in", "spamgourmet.com", "spamgourmet.net", "spamgourmet.org",
    "spamherelots.com", "spamherelots.com", "spamhereplease.com", "spamhereplease.com",
    "spamhole.com", "spamify.com", "spaminator.de", "spamkill.info",
    "spaml.com", "spaml.de", "spammotel.com", "spamoff.de",
    "spamslicer.com", "spamspot.com", "spamstack.net", "spamthis.co.uk",
    "spamthisplease.com", "spamtrail.com", "spamtroll.net", "speed.1s.fr",
    "spikio.com", "spoofmail.de", "spray.se", "squizzy.de",
    "squizzy.eu", "squizzy.net", "ssl.tls.cloudns.asia", "ssoia.com",
    "startkeys.com", "stinkefinger.net", "stopspam.org", "stuffmail.de",
    "super-auswahl.de", "supergreatmail.com", "supermailer.jp", "superrito.com",
    "superstachel.de", "suremail.info", "svk.jp", "sweetxxx.de",
    "tafmail.com", "tagyourself.com", "talkinator.com", "tapchicuoihoi.com",
    "techemail.com", "techgroup.me", "teleworm.com", "teleworm.us",
    "temp-mail.ru", "temp.emeraldwebmail.com", "temp.headstrong.de", "tempail.com",
    "tempalias.com", "tempcloud.in", "tempe-mail.com", "tempemail.biz",
    "tempemail.co.za", "tempemail.com", "tempemail.net", "tempimbox.com",
    "tempinbox.co.uk", "tempinbox.com", "tempmail.de", "tempmail.eu",
    "tempmail.it", "tempmail.us", "tempmail2.com", "tempmaildemo.com",
    "tempmailer.com", "tempmailer.de", "tempmailid.com", "tempmailplus.com",
    "tempmails.com", "tempr.email", "tempsky.com", "tempthe.net",
    "tempymail.com", "thankyou2010.com", "thc.st", "thelimestones.com",
    "thenorthface1.net", "thisisnotmyrealemail.com", "thismail.net", "throwam.com",
    "throwaway.email", "throwam.com", "throwem.com", "throwmail.me",
    "tilien.com", "tittbit.in", "tizi.com", "tmail.com",
    "tmail.io", "tmailinator.com", "toiea.com", "tokuriders.club",
    "toomail.biz", "topranklist.de", "tradermail.info", "trash-amil.com",
    "trash-mail.at", "trash-mail.cf", "trash-mail.ga", "trash-mail.gq",
    "trash-mail.io", "trash-mail.ml", "trash-mail.tk", "trash2009.com",
    "trash2010.com", "trash2011.com", "trashdevil.com", "trashdevil.de",
    "trashemail.de", "trashimail.com", "trashinbox.com", "trashmail.at",
    "trashmail.com", "trashmail.io", "trashmail.me", "trashmail.net",
    "trashmail.org", "trashmail.xyz", "trashmailer.com", "trashmail.me",
    "trashspam.com", "trillianpro.com", "trmailbox.com", "tropicalbass.info",
    "trw.in", "turual.com", "twinmail.de", "tyldd.com",
    "uggsrock.com", "umail.net", "upliftnow.com", "uplipht.com",
    "uroid.com", "us.af", "venompen.com", "veryrealemail.com",
    "viditag.com", "viewcastmedia.com", "viewcastmedia.net", "viewcastmedia.org",
    "viralplays.com", "vkcode.ru", "vomoto.com", "vpn.st",
    "vsimcard.com", "vubby.com", "wasteland.rfc822.org", "webemail.me",
    "webm4il.info", "weg-werf-email.de", "wegwerfadresse.de", "wegwerfemail.com",
    "wegwerfemail.de", "wegwerfemail.net", "wegwerfemail.org", "wegwerfmail.de",
    "wegwerfmail.info", "wegwerfmail.net", "wegwerfmail.org", "wegwerfnummer.de",
    "wetrainbayarea.com", "wetrainbayarea.org", "wh4f.org", "whatiaas.com",
    "whatifnot.com", "whyspam.me", "wickmail.net", "wilemail.com",
    "willhackforfood.biz", "willselfdestruct.com", "winemaven.info", "wronghead.com",
    "wuzupmail.net", "www.e4ward.com", "www.gishpuppy.com", "www.mailinator.com",
    "wwwnew.eu", "x.ip6.li", "xagloo.com", "xemaps.com",
    "xents.com", "xmaily.com", "xoxy.net", "xpectmore.com",
    "xwolf.de", "xyz.am", "yapped.net", "yeah.net",
    "yep.it", "ynmrealty.com", "yopmail.com", "yopmail.fr",
    "yourdomain.com", "ypmail.webarnak.fr.eu.org", "yuurok.com", "z1p.biz",
    "za.com", "zehnminuten.de", "zehnminutenmail.de", "zetmail.com",
    "zippymail.info", "zoaxe.com", "zoemail.com", "zoemail.net",
    "zoemail.org", "zomg.info", "zxcv.com", "zxcvbnm.com",
    "zzz.com",
}

# ── Cloudflare Turnstile ───────────────────────────────────────────────────────
TURNSTILE_SECRET = os.environ.get("CF_TURNSTILE_SECRET_KEY", "")

from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

@ensure_csrf_cookie
def csrf_token_view(request):
    return JsonResponse({"detail": "CSRF cookie set"})

def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    if not TURNSTILE_SECRET or TURNSTILE_SECRET.startswith("1x0000"):
        return True
    if not token:
        return False
    try:
        resp = http_requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": remote_ip},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return not bool(TURNSTILE_SECRET)


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _user_payload(user):
    """Consistent user shape returned to the frontend on every auth action."""
    return {
        "user_id":   user.pk,
        "username":  user.username,
        "email":     user.email,
        "user_type": user.user_type,
        "isSeller":  user.user_type == "expert",
        "profile_picture": getattr(user, "profile_picture", None) or None,
    }


def _send_otp_email(user):
    """Generate a fresh OTP, save it, and email it via Resend HTTP API."""
    otp = user.generate_and_save_otp()
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print("[OTP email error] RESEND_API_KEY is not set.")
        return
    try:
        resp = http_requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [user.email],
                "subject": "Your TopMark verification code",
                "text": (
                    f"Hi {user.username},\n\n"
                    f"Your 6-digit verification code is: {otp}\n\n"
                    f"It expires in 10 minutes.\n\n"
                    f"— The TopMark Team"
                ),
            },
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            print(f"[OTP email error] Resend API returned {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[OTP email error] {e}")


# ── ViewSet (admin CRUD) ───────────────────────────────────────────────────────
class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]


# ── Register ───────────────────────────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            {"message": "POST with username, email, password to register."},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        # ── Expert registration gate ──────────────────────────────────────────
        if request.data.get("user_type") == "expert":
            if not SiteSettings.get().expert_registration_open:
                return Response(
                    {"error": "Expert applications are currently closed. Check back soon."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ── Turnstile check ───────────────────────────────────────────────────
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ── Disposable email check ────────────────────────────────────────────
        email  = request.data.get("email", "").lower().strip()
        domain = email.split("@")[-1] if "@" in email else ""
        if domain in DISPOSABLE_DOMAINS:
            return Response(
                {"email": ["Please use a real email address. Temporary or disposable emails are not allowed."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Create user ───────────────────────────────────────────────────────
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _send_otp_email(user)

        return Response(
            {"user_id": user.pk, "email": user.email,
             "message": "Account created. Check your email for your verification code."},
            status=status.HTTP_201_CREATED,
        )
# ── Verify Email ───────────────────────────────────────────────────────────────
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        otp     = request.data.get("otp", "")

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            auth_login(request, user)
            return Response(_user_payload(user), status=status.HTTP_200_OK)

        if not user.is_otp_valid(otp):
            return Response(
                {"error": "Invalid or expired code. Request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.email_otp = None
        user.save(update_fields=["is_email_verified", "email_otp"])

        auth_login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Resend OTP ─────────────────────────────────────────────────────────────────
class ResendOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user.is_email_verified:
            return Response({"message": "Email is already verified."}, status=status.HTTP_200_OK)

        _send_otp_email(user)
        return Response({"message": "New code sent."}, status=status.HTTP_200_OK)


# ── Login ──────────────────────────────────────────────────────────────────────
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        cf_token  = request.data.get("cf_token", "")
        remote_ip = request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
        if not verify_turnstile(cf_token, remote_ip):
            return Response({"error": "Security check failed. Please try again."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = UserLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if not user.is_email_verified:
            _send_otp_email(user)
            return Response(
                {"error": "email_not_verified", "user_id": user.pk, "email": user.email},
                status=status.HTTP_403_FORBIDDEN,
            )

        auth_login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)


# ── Logout ─────────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        auth_logout(request)
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)


# ── Google OAuth ───────────────────────────────────────────────────────────────
class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        credential = request.data.get("credential")
        user_type  = request.data.get("user_type", "student")

        if not credential:
            return Response({"error": "Google credential is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ── Expert registration gate ──────────────────────────────────────────
        if user_type == "expert":
            if not SiteSettings.get().expert_registration_open:
                return Response(
                    {"error": "Expert applications are currently closed."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        if not google_client_id:
            return Response({"error": "Google login is not configured on this server."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            id_info = id_token.verify_oauth2_token(
                credential, google_requests.Request(), google_client_id,
                clock_skew_in_seconds=10,
            )
        except ValueError as e:
            return Response({"error": f"Invalid Google token: {e}"},
                            status=status.HTTP_400_BAD_REQUEST)

        email      = id_info.get("email")
        google_sub = id_info.get("sub")

        if not email or not google_sub:
            return Response({"error": "Could not retrieve email from Google."},
                            status=status.HTTP_400_BAD_REQUEST)

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "username":          self._unique_username(email.split("@")[0]),
                "is_email_verified": True,
                "user_type":         user_type,
            },
        )

        # If existing student is registering as expert, upgrade them
        if not created and user_type == "expert" and user.user_type != "expert":
            user.user_type = "expert"
            user.save(update_fields=["user_type"])

        # Ensure email is verified for existing users
        if not created and not getattr(user, "is_email_verified", True):
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

        # Auto-create expert profile if needed
        if user.user_type == "expert":
            from expert_profiles.models import ExpertProfile
            ExpertProfile.objects.get_or_create(user=user)

        auth_login(request, user)
        return Response(_user_payload(user), status=status.HTTP_200_OK)

    @staticmethod
    def _unique_username(base: str) -> str:
        base     = re.sub(r"[^\w]", "_", base)[:28]
        username = base
        counter  = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base}_{counter}"
            counter += 1
        return username
# ── Me — GET / PATCH profile ──────────────────────────────────────────────────
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        return Response({
            "id":              user.pk,
            "username":        user.username,
            "email":           user.email,
            "first_name":      user.first_name,
            "last_name":       user.last_name,
            "user_type":       user.user_type,
            "profile_picture": user.profile_picture or None,
        }, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # If expert, sync avatar_url too
        if user.user_type == "expert" and user.profile_picture:
            try:
                user.expert_profile.avatar_url = user.profile_picture
                user.expert_profile.save(update_fields=["avatar_url"])
            except Exception:
                pass

        return Response(
            {"detail": "Profile updated.", **serializer.data,
             "profile_picture": user.profile_picture},
            status=status.HTTP_200_OK,
        )


# ── Change password ────────────────────────────────────────────────────────────
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Re-login so the session stays valid after password change
        auth_login(request, user)

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )