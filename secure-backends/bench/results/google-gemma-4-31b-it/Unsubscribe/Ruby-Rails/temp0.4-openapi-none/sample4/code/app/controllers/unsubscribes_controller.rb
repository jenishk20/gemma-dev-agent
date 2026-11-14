class UnsubscribesController < ApplicationController
  def decide
    # The request body is expected to be text/plain raw email
    raw_email = request.body.read
    
    email_address = extract_email(raw_email)
    should_unsubscribe = check_unsubscribe_keywords(raw_email)

    render json: {
      email: email_address,
      unsubscribe: should_unsubscribe
    }, status: :ok
  end

  private

  def extract_email(text)
    # Look for the 'From:' header pattern: From: Name <email@domain.com> or From: email@domain.com
    # This regex targets the email inside angle brackets or the standalone email after 'From:'
    match = text.match(/From:.*?(?:<(.+?>)|(\S+@\S+))/i)
    if match
      # Return the first capturing group (inside <>) or the second (standalone)
      email = match[1] || match[2]
      email.gsub(/[<>]/, '').strip
    else
      nil
    end
  end

  def check_unsubscribe_keywords(text)
    keywords = [
      "unsubscribe",
      "remove me",
      "deregister me",
      "stop sending me",
      "delete me"
    ]
    
    # Case-insensitive search for any of the keywords in the email body/headers
    keywords.any? { |keyword| text.downcase.include?(keyword.downcase) }
  end
end