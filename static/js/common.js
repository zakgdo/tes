
function showAlert(msg, type = 'success') {
    alert(msg);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('已复制: ' + text);
    });
}


function toggleBookingDetails(tourId) {
    const detailsDiv = document.getElementById('booking-details-' + tourId);
    const toggleBtn = document.getElementById('toggle-btn-' + tourId);
    
    if (detailsDiv.style.display === 'none' || !detailsDiv.style.display) {
        detailsDiv.style.display = 'block';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-up"></i> 隐藏预订详情';
        
        // 如果内容为空，则加载预订详情
        if (detailsDiv.innerHTML.trim() === '') {
            loadBookingDetails(tourId);
        }
    } else {
        detailsDiv.style.display = 'none';
        toggleBtn.innerHTML = '<i class="fas fa-chevron-down"></i> 查看预订详情';
    }
}

async function loadBookingDetails(tourId) {
    try {
        const response = await fetch('/api/get_tour_bookings?tour_id=' + tourId);
        const result = await response.json();
        
        if (result.success) {
            const detailsDiv = document.getElementById('booking-details-' + tourId);
            let html = '';
            
            if (result.data.length === 0) {
                html = '<p style="text-align: center; color: #666;">暂无预订记录</p>';
            } else {
                html = '<table class="booking-table">';
                html += '<tr><th>预订码</th><th>姓名</th><th>手机</th><th>座位号</th><th>预订时间</th></tr>';
                
                for (const booking of result.data) {
                    const seatNumbers = Array.isArray(booking.seat_numbers) ? 
                        booking.seat_numbers.join(', ') : booking.seat_numbers;
                    
                    html += `<tr>
                        <td><strong>${booking.code}</strong></td>
                        <td>${booking.name}</td>
                        <td>${booking.phone}</td>
                        <td>${seatNumbers}</td>
                        <td>${booking.created_at}</td>
                    </tr>`;
                }
                
                html += '</table>';
            }
            
            detailsDiv.innerHTML = html;
        }
    } catch (error) {
        console.error('加载预订详情失败:', error);
        const detailsDiv = document.getElementById('booking-details-' + tourId);
        detailsDiv.innerHTML = '<p style="text-align: center; color: #e74c3c;">加载失败，请刷新页面重试</p>';
    }
}

function initSeatSelection() {
    let selectedSeats = [];
    
    window.selectSeat = function(element) {
        // 如果座位不可用，直接返回
        if (element.classList.contains('unavailable')) return;
        
        const seatNum = parseInt(element.getAttribute('data-seat'));
        const index = selectedSeats.indexOf(seatNum);
        
        if (index === -1) {
            // 选中座位
            selectedSeats.push(seatNum);
            element.classList.add('selected');
        } else {
            // 取消选中
            selectedSeats.splice(index, 1);
            element.classList.remove('selected');
        }
        
        // 更新显示
        document.getElementById('selectedSeatsDisplay').textContent = 
            selectedSeats.length > 0 ? selectedSeats.join(', ') : '无';
        document.getElementById('selectedSeatsInput').value = selectedSeats.join(',');
        
        // 隐藏警告
        const warningElement = document.getElementById('seatSelectionWarning');
        if (warningElement) {
            warningElement.style.display = 'none';
        }
    };
    
    window.submitBooking = async function(event, tourId) {
        event.preventDefault();
        
        // 验证是否选择了座位
        if (selectedSeats.length === 0) {
            document.getElementById('seatSelectionWarning').style.display = 'block';
            return;
        }
        
        const name = document.getElementById('customerName').value;
        const phone = document.getElementById('customerPhone').value;
        const seats = selectedSeats;
        
        const btn = event.target.querySelector('button[type="submit"]');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 提交中...';
        btn.disabled = true;
        
        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tour_id: tourId, 
                    name: name, 
                    phone: phone, 
                    seat_numbers: seats
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                document.getElementById('bookingForm').innerHTML = `
                    <div style="text-align: center; padding: 40px 20px;">
                        <i class="fas fa-check-circle" style="font-size: 4rem; color: #00b09b;"></i>
                        <h2>预订成功！</h2>
                        <p>您的座位已确认，请保存好预订码</p>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 25px 0; font-family: monospace;">
                            <p style="color: #666;">预订码</p>
                            <h1 style="color: #e74c3c; letter-spacing: 3px;">${result.booking_code}</h1>
                        </div>
                        <p><strong>已选座位：</strong>${seats.join(', ')}号</p>
                        <p><button class="btn" onclick="copyToClipboard('${result.booking_code}')" style="margin-top: 15px;">
                            <i class="fas fa-copy"></i> 复制预订码
                        </button></p>
                        <p style="margin-top: 20px;"><a href="/" class="btn" style="background: #6c757d;">返回首页</a></p>
                    </div>
                `;
            } else {
                alert('预订失败: ' + result.message);
                btn.innerHTML = '<i class="fas fa-check-circle"></i> 提交预订';
                btn.disabled = false;
            }
        } catch (error) {
            alert('网络错误，请重试');
            btn.innerHTML = '<i class="fas fa-check-circle"></i> 提交预订';
            btn.disabled = false;
        }
    };
}

function initAdminPage() {
    // 设置默认日期为明天
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dateInput = document.getElementById('newTourDate');
    if (dateInput) {
        dateInput.value = tomorrow.toISOString().split('T')[0];
    }
}

async function createTour(event) {
    event.preventDefault();
    
    const date = document.getElementById('newTourDate').value;
    const time = document.getElementById('newTourTime').value;
    const dest = document.getElementById('newTourDest').value;
    const vehicle = document.getElementById('newTourVehicle').value;
    const seats = parseInt(document.getElementById('newTourSeats').value);
    
    const response = await fetch('/api/create_tour', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            date: date, 
            time: time, 
            destination: dest, 
            vehicle_model: vehicle, 
            max_seats: seats 
        })
    });
    
    const result = await response.json();
    if (result.success) {
        alert('创建成功！页面将刷新...');
        location.reload();
    } else {
        alert('创建失败: ' + result.message);
    }
}

async function deleteTour(tourId) {
    if (!confirm('确定要删除这个班次吗？相关的所有预订也将被删除！')) return;
    
    const response = await fetch('/api/delete_tour', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tour_id: tourId })
    });
    
    const result = await response.json();
    if (result.success) {
        alert('删除成功！页面将刷新...');
        location.reload();
    } else {
        alert('删除失败: ' + result.message);
    }
}


document.addEventListener('DOMContentLoaded', function() {
    // 检查当前页面并初始化相应的功能
    if (document.querySelector('.book-page-grid')) {
        // 预订页面
        initSeatSelection();
    }
    
    if (document.querySelector('.admin-page')) {
        // 管理后台页面
        initAdminPage();
    }
    
    console.log('订车助手已加载完成');
});
