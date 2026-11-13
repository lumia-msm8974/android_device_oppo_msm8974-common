ifneq ($(filter bacon find7 martini,$(TARGET_DEVICE)),)
include $(call all-subdir-makefiles)
endif
