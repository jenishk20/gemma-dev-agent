class MonitoringController < ApplicationController
  # POST /heartbeat
  def heartbeat
    service_id = params[:serviceId]
    token = params[:token]

    if service_id.blank? || token.blank?
      return render json: { error: "Invalid request payload" }, status: :bad_request
    end

    # Find or create the service. If it exists, verify the token matches.
    service = Service.find_or_initialize_by(service_id: service_id)
    
    if service.new_record?
      service.token = token
    elsif service.token != token
      # If the token doesn't match the stored one, we treat it as an unauthorized/invalid request
      return render json: { error: "Invalid token" }, status: :bad_request
    end

    if service.save && service.register_heartbeat!
      head :ok
    else
      render json: { error: "Could not save service" }, status: :internal_server_error
    end
  end

  # POST /services
  def services
    token = params[:token]

    if token.blank?
      return render json: { error: "Token is required" }, status: :bad_request
    end

    # Find all services that match the provided token
    services = Service.where(token: token)

    # Map to the response format specified in OpenAPI
    response = services.map do |s|
      {
        serviceId: s.service_id,
        lastNotification: s.last_notification&.iso8601
      }
    end

    render json: response, status: :ok
  end
end