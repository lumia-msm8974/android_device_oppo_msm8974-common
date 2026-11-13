ifneq ($(filter bacon find7 martini bandit,$(TARGET_DEVICE)),)
include $(call all-subdir-makefiles)
endif
