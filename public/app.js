/**
 * Notion Quick Schedule Mobile Application Logic
 * 5대 분류 선택, 종일/시간 일정 토글, 비동기 노션 등록 및 토스트 피드백
 */

document.addEventListener('DOMContentLoaded', () => {
  
  // 상태 변수
  let selectedCategory = '회사 : 작업';
  let isRangeActive = false;

  // DOM 요소 참조
  const form = document.getElementById('schedule_form');
  const inputTitle = document.getElementById('input_title');
  const inputMemo = document.getElementById('input_memo');
  const toggleAllDay = document.getElementById('toggle_all_day');
  const inputStartDate = document.getElementById('input_start_date');
  const inputStartTime = document.getElementById('input_start_time');
  const inputEndDate = document.getElementById('input_end_date');
  const inputEndTime = document.getElementById('input_end_time');
  const wrapperStartTime = document.getElementById('wrapper_start_time');
  const wrapperEndTime = document.getElementById('wrapper_end_time');
  const wrapperEndDateGroup = document.getElementById('wrapper_end_date_group');
  const btnToggleEndDate = document.getElementById('btn_toggle_end_date');
  const labelStartDate = document.getElementById('label_start_date');
  const btnSubmit = document.getElementById('btn_submit');
  const submitLoader = document.getElementById('submit_loader');
  const toastContainer = document.getElementById('toast_container');
  const connectionBadge = document.getElementById('connection_badge');
  const badgeText = document.getElementById('badge_text');
  const categoryChips = document.querySelectorAll('.category_chip');

  // 1. 초기 날짜 및 시간 기본값 설정
  function initDefaultDateTime() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(Math.ceil(now.getMinutes() / 10) * 10).padStart(2, '0');

    const todayStr = `${year}-${month}-${day}`;
    const timeStr = `${hours}:${minutes}`;

    inputStartDate.value = todayStr;
    inputStartTime.value = timeStr;
    inputEndDate.value = todayStr;
    inputEndTime.value = `${String(Math.min(23, Number(hours) + 1)).padStart(2, '0')}:${minutes}`;
  }

  initDefaultDateTime();

  // 2. 5대 분류 칩 선택 인터랙션
  categoryChips.forEach(chip => {
    chip.addEventListener('click', () => {
      categoryChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedCategory = chip.getAttribute('data-category');
      
      // 햅틱 피드백
      if (navigator.vibrate) {
        navigator.vibrate(10);
      }
    });
  });

  // 3. 종일 일정 토글 인터랙션
  toggleAllDay.addEventListener('change', () => {
    const isAllDay = toggleAllDay.checked;
    if (isAllDay) {
      wrapperStartTime.classList.add('hidden');
      wrapperEndTime.classList.add('hidden');
      labelStartDate.textContent = '날짜';
    } else {
      wrapperStartTime.classList.remove('hidden');
      if (isRangeActive) {
        wrapperEndTime.classList.remove('hidden');
      }
      labelStartDate.textContent = '시작 날짜';
    }
  });

  // 4. 기간(종료일) 추가/숨김 토글
  btnToggleEndDate.addEventListener('click', () => {
    isRangeActive = !isRangeActive;
    if (isRangeActive) {
      wrapperEndDateGroup.classList.remove('hidden');
      btnToggleEndDate.innerHTML = '<span class="plus_icon">✕</span> 기간(종료일) 제거';
      if (!toggleAllDay.checked) {
        wrapperEndTime.classList.remove('hidden');
      }
    } else {
      wrapperEndDateGroup.classList.add('hidden');
      btnToggleEndDate.innerHTML = '<span class="plus_icon">+</span> 기간(종료일) 추가';
      inputEndDate.value = '';
    }
  });

  // 5. 토스트 알림 메시지 표시
  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast_item toast_${type}`;
    const icon = type === 'success' ? '✅' : '⚠️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px) scale(0.95)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 2800);
  }

  // 6. 서버 헬스체크 및 노션 연동 상태 조회
  async function checkServerHealth() {
    const endpoints = ['/api/health', '/health', '/api'];
    let data = null;

    for (const url of endpoints) {
      try {
        const res = await fetch(url);
        if (res.ok) {
          data = await res.json();
          break;
        }
      } catch (e) {
        // 다음 엔드포인트 시도
      }
    }

    if (data) {
      if (data.notion_status && data.notion_status.success) {
        connectionBadge.className = 'badge_online';
        badgeText.textContent = '노션 연결됨';
      } else if (!data.notion_configured) {
        connectionBadge.className = 'badge_offline';
        badgeText.textContent = '토큰 미설정';
      } else {
        connectionBadge.className = 'badge_offline';
        badgeText.textContent = '권한 확인 필요';
      }
    } else {
      connectionBadge.className = 'badge_offline';
      badgeText.textContent = '서버 확인 필요';
    }
  }

  checkServerHealth();

  // 7. 폼 제출(Submit) 이벤트
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = inputTitle.value.trim();
    if (!title) {
      showToast('일정 제목을 입력해주세요.', 'error');
      inputTitle.focus();
      return;
    }

    const isAllDay = toggleAllDay.checked;
    let startVal = inputStartDate.value;
    let endVal = null;

    if (!isAllDay && inputStartTime.value) {
      startVal = `${inputStartDate.value}T${inputStartTime.value}`;
    }

    if (isRangeActive && inputEndDate.value) {
      if (!isAllDay && inputEndTime.value) {
        endVal = `${inputEndDate.value}T${inputEndTime.value}`;
      } else {
        endVal = inputEndDate.value;
      }
    }

    const payload = {
      title: title,
      category: selectedCategory,
      is_all_day: isAllDay,
      start_date: startVal,
      end_date: endVal,
      memo: inputMemo.value.trim() || null
    };

    // UI 로딩 상태 전환
    btnSubmit.disabled = true;
    submitLoader.classList.remove('hidden');

    try {
      const endpoints = ['/api/schedule', '/schedule', '/api'];
      let lastResponse = null;
      let lastResult = null;

      for (const ep of endpoints) {
        try {
          const res = await fetch(ep, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
          });
          lastResponse = res;
          lastResult = await res.json();
          if (res.ok && lastResult.success) {
            break;
          }
          if (res.status !== 404) {
            break;
          }
        } catch (err) {
          // 다음 엔드포인트 시도
        }
      }

      if (lastResponse && lastResponse.ok && lastResult && lastResult.success) {
        showToast('노션에 일정이 등록되었습니다!', 'success');
        
        if (navigator.vibrate) {
          navigator.vibrate([15, 30, 15]);
        }

        // 입력 폼 초기화
        inputTitle.value = '';
        inputMemo.value = '';
        inputTitle.focus();
      } else {
        const errorMsg = (lastResult && (lastResult.error || lastResult.detail)) || '등록에 실패했습니다.';
        showToast(`등록 실패: ${errorMsg}`, 'error');
      }
    } catch (error) {
      showToast('서버 통신 오류가 발생했습니다.', 'error');
    } finally {
      btnSubmit.disabled = false;
      submitLoader.classList.add('hidden');
    }
  });

});
