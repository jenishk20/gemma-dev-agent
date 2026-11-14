class MonitoringController < ApplicationController
  # POST /heartbeat
  def heartbeat
    service_id = params[:serviceId]
    token = params[:token]

    if service_id.blank? || token.blank?
      return render json: { error: 'Invalid request payload' }, status: :bad_request
    end

    # Find existing record or create a new one for this service
    service = ServiceStatus.find_or_initialize_by(service_id: service_id)
    
    # Update the token and the last notification timestamp
    service.token = token
    service.last_notification_at = Time.current
    
    if service.save
      head :ok
    else
      render json: { error: 'Internal server error' }, status: :internal_server_error
    end
  end

  # POST /services
  def services
    token = params[:token]

    if token.blank?
      return render json: { error: 'Token is required' }, status: :bad_request
    end

    # Find all services that match the provided token
    services = ServiceStatus.where(token: token)
    
    # Map to the requested OpenAPI response format
    response = services.map do |s|
      {
        serviceId: s.service_id,
        lastNotification: s.last_notification_at.iso8601
      }
    end

    render json: response, status: :ok
  end
end