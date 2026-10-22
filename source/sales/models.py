from shared.models import *

class Lead(CompanyOwned,TimeStamped):
    # Temperature scale to measure (subjectively qualify) a lead's enthusiasm about the product
    class Temperature(models.TextChoices):
        ICE         = "I"   ,"Ice"
        COLD        = "CD"  ,"Cold"
        COOL        = "CL"  ,"Cool"
        NEUTRAL     = "N"   ,"Neutral"
        LUKEWARM    = "LW"  ,"Lukewarm"
        WARM        = "W"   ,"Warm" 
        HOT         = "H"   ,"Hot"

    class LeadStatus(models.TextChoices):
        NEW         = "NL", "New Lead"
        OPEN        = "OL", "Open Lead"
        QUOTED      = "QO", "Quoted Lead"
        IN_PROGRESS = "IP", "In Progress"
        LOST        = "LL", "Lost Lead"
        WON         = "WL", "Won Lead"

    class SaleStage(models.TextChoices):
        NEW         = "N", "New"
        PROSPECTED  = "P", "Prospected"
        QUALIFIED   = "Q", "Qualified"
        ENGAGED     = "E", "Engaged"
        AWAITING    = "A", "Awaiting"
        CLOSED      = "C", "Closed"

    entity              = models.ForeignKey(Entity,on_delete=models.PROTECT,related_name="leads")
    source              = models.ForeignKey(Source,on_delete=models.SET_NULL,null=True,blank=True)
    description         = models.TextField(max_length=1000, null=True, blank=True)
    status              = models.CharField(choices=LeadStatus.choices, default=LeadStatus.NEW)
    stage               = models.CharField(choices=SaleStage.choices, default=SaleStage.NEW)
    size                = models.IntegerField(null=True,blank=True,default=1)
    qualifying_score    = models.SmallIntegerField(null=True,blank=True)
    temperature         = models.CharField(choices=Temperature.choices, default=Temperature.NEUTRAL)
    responsiveness      = models.DateTimeField(null=True,blank=True)
    turn                = models.BooleanField(default=False)
    