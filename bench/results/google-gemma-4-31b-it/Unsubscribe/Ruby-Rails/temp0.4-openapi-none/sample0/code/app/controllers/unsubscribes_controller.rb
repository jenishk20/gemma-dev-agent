class UnsubscribesController < ApplicationController
  # Keywords defined in the OpenAPI specification
  UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe",
    "remove me",
    "deregister me",
    "stop sending me",
    "delete me"
  ].freeze

  def decide
    # The request body is text/plain as per OpenAPI spec
    raw_email = request.body.read
    
    if raw_email.blank?
      return render json: { error: "Empty request body" }, status: :bad_request
    end

    email_address = extract_email(raw_email)
    should_unsubscribe = check_for_unsubscribe_request(raw_email)

    render json: {
      email: email_address,
      unsubscribe: should_unsubscribe
    }, status: :ok
  end

  private

  def extract_email(text)
    # Look for the 'From:' header in the raw email
    # Matches "From: Name <email@domain.com>" or "From: email@domain.com"
    if text =~ /^From:.*<(.+@.+)>/i
      $1
    elsif text =~ /^From:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i
      $1
    else
      "unknown"
    end
  end

  def check_for_unsubscribe_request(text)
    # Convert to lowercase for case-insensitive matching
    content = text.downcase
    UNSUBSCRIBE_KEYWORDS.any? { |keyword| content.include?(keyword) }
  end
end