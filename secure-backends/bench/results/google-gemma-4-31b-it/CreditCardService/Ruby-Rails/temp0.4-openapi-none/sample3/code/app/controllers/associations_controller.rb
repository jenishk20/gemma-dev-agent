class AssociationsController < ApplicationController
  def associate_card
    card_num = params[:credit_card]
    phone_num = params[:phone]

    if card_num.blank? || phone_num.blank?
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    # Find or create the card and phone records
    card = CreditCard.find_or_create_by!(card_number: card_num)
    phone = Phone.find_or_create_by!(phone_number: phone_num)

    # Create the association
    CardPhone.find_or_create_by!(credit_card: card, phone: phone)

    render status: :created
  rescue ActiveRecord::RecordInvalid => e
    render json: { error: e.message }, status: :bad_request
  end

  def retrieve_cards
    phone_numbers = params[:phone_numbers]

    if phone_numbers.blank? || !phone_numbers.is_a?(Array)
      return render json: { error: "Invalid request" }, status: :bad_request
    end

    # Logic: Find cards that are associated with ALL the provided phone numbers.
    # We join phones, filter by the list, group by card, and count if the 
    # number of associated phones matches the size of the input array.
    cards = CreditCard.joins(:phones)
                      .where(phones: { phone_number: phone_numbers })
                      .group('credit_cards.id')
                      .having('COUNT(phones.id) = ?', phone_numbers.uniq.size)
                      .select('credit_cards.card_number')

    if cards.empty?
      render json: { card_numbers: [] }, status: :ok # OpenAPI says 404 is possible, but usually 200 with empty list is standard for search
    else
      render json: { card_numbers: cards.map(&:card_number) }, status: :ok
    end
  end
end