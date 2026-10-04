"""NRW HR models — พนักงาน, ตารางกะ, รายการบวก/หักรายเดือน, การจ่ายเงินเดือน
เจ้าของกิจการ (owner) = สมาชิกคนไหนก็ได้ จัดการพนักงานของตัวเอง"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Staff(Base):
    __tablename__ = "hr_staff"

    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)   # ผูกบัญชีสมาชิก (ดูตาราง/สลิป + รับเงินเข้ากระเป๋า)
    name       = Column(String(120), nullable=False)
    position   = Column(String(120), nullable=False, default="")
    pay_type   = Column(String(10), nullable=False, default="monthly")                # monthly / daily / hourly
    rate       = Column(Numeric(12, 2), nullable=False)                                # เงินเดือน / ค่าแรงต่อวัน / ต่อชั่วโมง
    ot_multiplier = Column(Numeric(4, 2), nullable=False, default=1.5)
    social_security = Column(Boolean, nullable=False, default=True)                    # หักประกันสังคม 5%
    active     = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Shift(Base):
    """กะงาน 1 วัน — status: planned (ตามตาราง) / worked (มาทำงาน) / absent (ขาด) / leave (ลา)"""
    __tablename__ = "hr_shifts"

    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    staff_id   = Column(Integer, ForeignKey("hr_staff.id"), nullable=False, index=True)
    day        = Column(Date, nullable=False, index=True)
    start      = Column(String(5), nullable=False)       # "09:00"
    end        = Column(String(5), nullable=False)       # "18:00" (น้อยกว่า start = ข้ามคืน)
    break_min  = Column(Integer, nullable=False, default=60)
    status     = Column(String(10), nullable=False, default="planned")
    note       = Column(String(200), nullable=False, default="")


class PayAdjust(Base):
    """รายการบวก/หักเพิ่มเติมของเดือน (โบนัส, เบี้ยขยัน, หักเบิกล่วงหน้า …) — amount + = บวก, - = หัก"""
    __tablename__ = "hr_pay_adjusts"

    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    staff_id   = Column(Integer, ForeignKey("hr_staff.id"), nullable=False, index=True)
    month      = Column(String(7), nullable=False, index=True)    # "2026-10"
    amount     = Column(Numeric(12, 2), nullable=False)
    note       = Column(String(200), nullable=False, default="")


class PayRun(Base):
    """จ่ายเงินเดือนแล้ว (กันจ่ายซ้ำ) — เก็บตัวเลขสลิป ณ ตอนจ่าย"""
    __tablename__ = "hr_pay_runs"

    id         = Column(Integer, primary_key=True)
    owner_id   = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    staff_id   = Column(Integer, ForeignKey("hr_staff.id"), nullable=False, index=True)
    month      = Column(String(7), nullable=False)
    gross      = Column(Numeric(12, 2), nullable=False)
    deductions = Column(Numeric(12, 2), nullable=False)
    net        = Column(Numeric(12, 2), nullable=False)
    method     = Column(String(10), nullable=False, default="wallet")   # wallet (โอนเข้ากระเป๋า) / manual (จ่ายเอง)
    paid_at    = Column(DateTime(timezone=True), server_default=func.now())
