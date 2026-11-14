class UnsubscribesController < ApplicationController
  def decide
    # The request body is raw text/plain as per OpenAPI spec
    raw_email = request.body.read
    
    email_address = extract_email(raw_email)
    should_unsubscribe = check_unsubscribe_intent(raw_email)

    render json: {
      email: email_address,
      unsubscribe: should_unsubscribe
    }, status: :ok
  end

  private

  def extract_email(text)
    # Look for the 'From:' header pattern: From: Name <email@domain.com> or From: email@domain.com
    # This regex looks for the email inside angle brackets or the word immediately following 'From:'
    if text =~ /^From:\s*(?:.*<)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:>)?/i
      return $1
    end
    nil
  end

  def check_unsubscribe_intent(text)
    keywords = [
      "unsubscribe",
      "remove me",
      "deregister me",
      "stop sending me",
      "delete me"
    ]
    
    # Convert to lowercase for case-insensitive matching
    content = text.downcase
    keywords.any? { |phrase| content.include?(phrase) }
  end
end